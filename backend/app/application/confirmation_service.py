"""Proposal 预检查与确认写入用例。

- precheck：只校验、不写入，返回每项余额预览；
- confirm：先统一校验全部操作，再在单个事务中写入，任一失败整组回滚；
- 幂等：同一建议只能从 pending 成功确认一次。
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.application import serializers
from app.domain.errors import DomainError, NotFoundError
from app.domain.rules import (
    ensure_positive_int,
    validate_consume_quantity,
    validate_display_name,
    validate_package_counts,
)
from app.infrastructure.models import Customer
from app.repositories import customers as customer_repo
from app.repositories import ledger as ledger_repo
from app.repositories import packages as package_repo
from app.repositories import proposals as proposal_repo
from app.repositories import services as service_repo
from app.schemas.agent import ConfirmRequest, PrecheckRequest


def _today() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).date().isoformat()


def _get_pending_proposal(db: Session, proposal_id: int):
    proposal = proposal_repo.get_proposal(db, proposal_id)
    if proposal is None:
        raise NotFoundError("解析记录不存在")
    if proposal.status != "pending":
        raise DomainError("该建议已处理，不能重复确认")
    return proposal


def _resolve_customer_confirm(db: Session, customer_data) -> Customer:
    if customer_data.customer_id is not None:
        customer = customer_repo.get_customer(db, customer_data.customer_id)
        if customer is None:
            raise DomainError("选择的客户不存在或已删除")
        return customer
    if customer_data.new_customer is not None:
        display_name = validate_display_name(customer_data.new_customer.display_name)
        aliases = _clean_aliases(customer_data.new_customer.aliases)
        return customer_repo.create_customer(db, display_name, aliases)
    raise DomainError("请选择已有客户或填写新客户")


def _resolve_customer_precheck(db: Session, customer_data) -> Customer:
    if customer_data.customer_id is not None:
        customer = customer_repo.get_customer(db, customer_data.customer_id)
        if customer is None:
            raise DomainError("选择的客户不存在或已删除")
        return customer
    if customer_data.new_customer is not None:
        display_name = validate_display_name(customer_data.new_customer.display_name)
        return Customer(display_name=display_name, id=None)  # 临时对象，不写入
    raise DomainError("请选择已有客户或填写新客户")


def _clean_aliases(aliases) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in aliases or []:
        name = str(raw).strip()
        if name and name not in seen:
            seen.add(name)
            result.append(name)
    return result


def precheck(db: Session, proposal_id: int, data: PrecheckRequest) -> dict:
    proposal = _get_pending_proposal(db, proposal_id)
    customer = _resolve_customer_precheck(db, data.customer)
    actions = [_validate_action(db, customer, a) for a in data.actions]
    return {
        "id": proposal.id,
        "ok": all(a["ok"] for a in actions),
        "customer": _customer_view(customer),
        "actions": actions,
    }


def confirm(db: Session, proposal_id: int, data: ConfirmRequest) -> dict:
    proposal = _get_pending_proposal(db, proposal_id)
    customer = _resolve_customer_confirm(db, data.customer)

    # 统一校验：全部通过才写入
    validations = [_validate_action(db, customer, a) for a in data.actions]
    errors = [v for v in validations if not v["ok"]]
    if errors:
        raise DomainError("；".join(v["error"] for v in errors))

    try:
        results = [_execute_action(db, customer, a, proposal) for a in data.actions]
        proposal_repo.mark_confirmed(db, proposal)
        serializers.save(db)
    except Exception:
        db.rollback()
        raise

    return {
        "id": proposal.id,
        "status": "confirmed",
        "customer": serializers.customer_to_dict(customer),
        "results": results,
    }


def _customer_view(customer: Customer) -> dict:
    if customer.id is None:
        return {"id": None, "display_name": customer.display_name, "is_new": True}
    return {**serializers.customer_to_dict(customer), "is_new": False}


def _package_candidates(db: Session, packages) -> list[dict]:
    used_counts = package_repo.compute_used_counts(db, packages)
    return [
        {
            "id": p.id,
            "total_count": p.total_count,
            "used_count": used_counts[p.id],
            "remaining_count": p.total_count - used_counts[p.id],
            "purchased_on": p.purchased_on,
            "price_cents": p.price_cents,
        }
        for p in packages
    ]


def _resolve_consume(db: Session, customer: Customer, action):
    """返回 (package, error, preview)。多卡未选择时返回 candidates。"""
    if action.service_id is None:
        return None, "核销需要选择服务项目", None
    service = service_repo.get_service(db, action.service_id)
    if service is None:
        return None, "服务项目不存在或已删除", None
    try:
        quantity = ensure_positive_int(action.quantity or 1, "核销数量")
    except DomainError as exc:
        return None, str(exc), None

    packages = [
        p
        for p in package_repo.list_packages_for_customer_service(db, customer.id, service.id)
        if p.status != "inactive"
    ]
    if not packages:
        return None, f"客户「{customer.display_name}」没有「{service.name}」的套餐，请先购买套餐或改为一次性服务", None

    package = None
    if action.package_id is not None:
        for p in packages:
            if p.id == action.package_id:
                package = p
                break
        if package is None:
            return None, "所选套餐卡不存在或不属于该客户/服务", None
    else:
        if len(packages) > 1:
            return None, "该客户有多张同类套餐卡，请选择使用哪一张", _package_candidates(db, packages)
        package = packages[0]

    used = package_repo.compute_used_count(db, package)
    try:
        validate_consume_quantity(package.total_count, used, quantity)
    except DomainError as exc:
        return None, str(exc), None

    preview = {
        "package_id": package.id,
        "total_count": package.total_count,
        "used_count": used,
        "used_after": used + quantity,
        "remaining_count": package.total_count - used - quantity,
    }
    return package, None, preview


def _validate_action(db: Session, customer: Customer, action) -> dict:
    action_type = action.type

    if action_type == "create_package":
        if action.service_id is None:
            return _fail("create_package", "购买套餐需要选择服务项目")
        service = service_repo.get_service(db, action.service_id)
        if service is None:
            return _fail("create_package", "服务项目不存在或已删除")
        if service.status != "active":
            return _fail("create_package", "已停用或删除的服务不能建立新套餐")
        if action.total_count is None:
            return _fail("create_package", "购买套餐需要填写总次数")
        try:
            validate_package_counts(action.total_count, 0)
        except DomainError as exc:
            return _fail("create_package", str(exc))
        return _ok("create_package", {"total_count": action.total_count, "remaining_count": action.total_count})

    if action_type == "consume_service":
        _, error, preview = _resolve_consume(db, customer, action)
        if error:
            return _fail("consume_service", error, preview)
        return _ok("consume_service", preview)

    if action_type == "record_one_time_service":
        if action.service_id is None:
            return _fail("record_one_time_service", "一次性服务需要选择服务项目")
        service = service_repo.get_service(db, action.service_id)
        if service is None:
            return _fail("record_one_time_service", "服务项目不存在或已删除")
        try:
            quantity = ensure_positive_int(action.quantity or 1, "数量")
        except DomainError as exc:
            return _fail("record_one_time_service", str(exc))
        return _ok("record_one_time_service", {"quantity": quantity})

    if action_type == "record_product_purchase":
        if not action.product_name or not str(action.product_name).strip():
            return _fail("record_product_purchase", "商品购买需要填写商品名称")
        try:
            quantity = ensure_positive_int(action.quantity or 1, "数量")
        except DomainError as exc:
            return _fail("record_product_purchase", str(exc))
        return _ok("record_product_purchase", {"quantity": quantity, "product_name": str(action.product_name).strip()})

    if action_type == "query_customer":
        return _ok("query_customer", None)

    return _fail(action_type, f"不支持的操作类型：{action_type}")


def _ok(action_type, preview):
    return {"type": action_type, "ok": True, "error": None, "preview": preview}


def _fail(action_type, error, candidates=None):
    return {"type": action_type, "ok": False, "error": error, "candidates": candidates}


def _execute_action(db: Session, customer: Customer, action, proposal) -> dict:
    action_type = action.type
    occurred_on = action.occurred_on or _today()

    if action_type == "create_package":
        return _do_create_package(db, customer, action, proposal)
    if action_type == "consume_service":
        return _do_consume_service(db, customer, action, proposal, occurred_on)
    if action_type == "record_one_time_service":
        return _do_one_time_service(db, customer, action, proposal, occurred_on)
    if action_type == "record_product_purchase":
        return _do_product_purchase(db, customer, action, proposal, occurred_on)
    if action_type == "query_customer":
        return _do_query_customer(db, customer)
    raise DomainError(f"不支持的操作类型：{action_type}")


def _do_create_package(db: Session, customer: Customer, action, proposal) -> dict:
    service = service_repo.get_service(db, action.service_id)
    total, _ = validate_package_counts(action.total_count, 0)
    package = package_repo.create_package(
        db, customer.id, service.id, total, 0, action.price_cents, action.purchased_on
    )
    ledger_repo.create_ledger_entry(
        db,
        customer_id=customer.id,
        entry_type="package_purchase",
        service_id=service.id,
        package_id=package.id,
        product_name=None,
        quantity=total,
        price_cents=action.price_cents,
        occurred_on=action.occurred_on or _today(),
        original_input=proposal.original_input,
        agent_prompt_version=proposal.prompt_version,
    )
    return {
        "type": "create_package",
        "message": f"已创建套餐「{service.name}」共 {total} 次。",
        "occurred_on": action.occurred_on or _today(),
        "package_id": package.id,
        "remaining_count": total,
    }


def _do_consume_service(db: Session, customer: Customer, action, proposal, occurred_on: str) -> dict:
    package, _, preview = _resolve_consume(db, customer, action)
    service = service_repo.get_service(db, action.service_id)
    ledger_repo.create_ledger_entry(
        db,
        customer_id=customer.id,
        entry_type="package_consumption",
        service_id=service.id,
        package_id=package.id,
        product_name=None,
        quantity=ensure_positive_int(action.quantity or 1, "核销数量"),
        price_cents=None,
        occurred_on=occurred_on,
        original_input=proposal.original_input,
        agent_prompt_version=proposal.prompt_version,
    )
    return {
        "type": "consume_service",
        "message": f"已累计使用 {preview['used_after']}/{preview['total_count']} 次，还剩 {preview['remaining_count']} 次。",
        "occurred_on": occurred_on,
        "package_id": package.id,
        "remaining_count": preview["remaining_count"],
    }


def _do_one_time_service(db: Session, customer: Customer, action, proposal, occurred_on: str) -> dict:
    service = service_repo.get_service(db, action.service_id)
    quantity = ensure_positive_int(action.quantity or 1, "数量")
    ledger_repo.create_ledger_entry(
        db,
        customer_id=customer.id,
        entry_type="one_time_service",
        service_id=service.id,
        package_id=None,
        product_name=None,
        quantity=quantity,
        price_cents=action.price_cents,
        occurred_on=occurred_on,
        original_input=proposal.original_input,
        agent_prompt_version=proposal.prompt_version,
    )
    return {
        "type": "record_one_time_service",
        "message": f"已消费 {quantity} 次 {service.name} 服务。",
        "occurred_on": occurred_on,
        "service_id": service.id,
    }


def _do_product_purchase(db: Session, customer: Customer, action, proposal, occurred_on: str) -> dict:
    product_name = str(action.product_name).strip()
    quantity = ensure_positive_int(action.quantity or 1, "数量")
    ledger_repo.create_ledger_entry(
        db,
        customer_id=customer.id,
        entry_type="product_purchase",
        service_id=None,
        package_id=None,
        product_name=product_name,
        quantity=quantity,
        price_cents=action.price_cents,
        occurred_on=occurred_on,
        original_input=proposal.original_input,
        agent_prompt_version=proposal.prompt_version,
    )
    return {
        "type": "record_product_purchase",
        "message": f"已记录购买 {product_name} 共 {quantity} 件。",
        "occurred_on": occurred_on,
        "product_name": product_name,
    }


def _do_query_customer(db: Session, customer: Customer) -> dict:
    packages = package_repo.list_packages_for_customer(db, customer.id)
    entries = ledger_repo.list_ledger_for_customer(db, customer.id)
    summary = serializers.customer_to_dict(customer)
    summary["packages"] = serializers.packages_to_dicts(db, packages)
    summary["ledger"] = [serializers.ledger_to_dict(e) for e in entries]
    return {
        "type": "query_customer",
        "message": f"已查询客户「{customer.display_name}」。",
        "customer": summary,
    }
