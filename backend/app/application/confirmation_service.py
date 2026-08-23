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
from app.application.fact_extraction_service import ALLOWED_FACT_TYPES, normalize_fact_value
from app.application.product_resolution_service import normalize_product_text, resolve_product
from app.repositories import customer_facts as fact_repo
from app.repositories import products as product_repo
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
    if customer_data is None:
        raise DomainError("该操作需要选择客户")
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
        if customer is None:
            return _fail("record_product_purchase", "商品购买需要选择客户")
        if action.product_id is not None:
            product = product_repo.get_product(db, action.product_id)
            if product is None:
                return _fail("record_product_purchase", "选择的产品不存在、已停用或已合并")
        elif not action.create_product and not (action.product_name and action.product_name.strip()):
            return _fail("record_product_purchase", "商品购买需要选择已有产品或确认新增产品")
        if action.create_product and not (action.canonical_name or action.product_name):
            return _fail("record_product_purchase", "商品购买需要填写商品名称")
        if action.create_product:
            matched = resolve_product(
                db, action.canonical_name or action.product_name,
                brand=action.brand, specification=action.specification,
            )
            if matched["status"] == "exact":
                return _fail("record_product_purchase", "确认期间已出现相同产品，请重新选择现有产品")
        try:
            quantity = ensure_positive_int(action.quantity or 1, "数量")
        except DomainError as exc:
            return _fail("record_product_purchase", str(exc))
        return _ok("record_product_purchase", {
            "quantity": quantity,
            "product_id": action.product_id,
            "product_name": str(action.canonical_name or action.product_name or product.canonical_name).strip(),
            "creates_draft": bool(action.create_product),
        })

    if action_type == "upsert_customer_fact":
        if customer is None:
            return _fail(action_type, "客户事实需要选择客户")
        if action.fact_type not in ALLOWED_FACT_TYPES:
            return _fail(action_type, "客户事实类型不在白名单内")
        if not action.display_value or not action.evidence_text:
            return _fail(action_type, "客户事实必须保留展示值和原话证据")
        if action.sensitivity_level not in {"normal", "sensitive"}:
            return _fail(action_type, "客户事实敏感级别无效")
        current = fact_repo.get_current_by_type(db, customer.id, action.fact_type)
        if current and current.normalized_value != normalize_fact_value(action.display_value):
            if action.supersedes_id != current.id:
                return _fail(action_type, "客户事实版本已变化，请重新确认")
        return _ok(action_type, {
            "fact_type": action.fact_type,
            "display_value": action.display_value,
            "sensitive": action.sensitivity_level == "sensitive",
            "supersedes_id": current.id if current else None,
        })

    if action_type == "delete_customer_fact":
        if customer is None or action.fact_id is None:
            return _fail(action_type, "删除客户事实需要客户和事实ID")
        current = fact_repo.get_current_by_type(db, customer.id, action.fact_type)
        if current is None or current.id != action.fact_id:
            return _fail(action_type, "要删除的客户事实已变化，请重新确认")
        if not action.evidence_text:
            return _fail(action_type, "删除客户事实必须保留店主原话证据")
        return _ok(action_type, {
            "fact_id": current.id, "fact_type": current.fact_type,
            "display_value": current.display_value,
        })

    if action_type == "create_product":
        name = str(action.canonical_name or "").strip()
        if not name:
            return _fail(action_type, "新增产品需要标准名称")
        matched = resolve_product(
            db, name, brand=action.brand, specification=action.specification
        )
        if matched["status"] == "exact":
            return _fail(action_type, "已存在相同产品，请选择现有产品或先处理重复项")
        return _ok(action_type, {"canonical_name": name, "knowledge_status": "incomplete"})

    if action_type == "merge_product":
        if not action.source_product_id or not action.target_product_id:
            return _fail(action_type, "合并产品需要来源和保留产品")
        if action.source_product_id == action.target_product_id:
            return _fail(action_type, "不能把产品合并到自身")
        if not product_repo.get_product(db, action.source_product_id):
            return _fail(action_type, "来源产品不存在、已停用或已合并")
        if not product_repo.get_product(db, action.target_product_id):
            return _fail(action_type, "保留产品不存在、已停用或已合并")
        return _ok(action_type, {
            "source_product_id": action.source_product_id,
            "target_product_id": action.target_product_id,
        })

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
    if action_type == "upsert_customer_fact":
        return _do_customer_fact(db, customer, action, proposal)
    if action_type == "delete_customer_fact":
        return _do_delete_customer_fact(db, customer, action, proposal)
    if action_type == "create_product":
        return _do_create_product(db, action)
    if action_type == "merge_product":
        return _do_merge_product(db, action)
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
    package, error, preview = _resolve_consume(db, customer, action)
    if error:
        raise DomainError(error)
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
    product = product_repo.get_product(db, action.product_id) if action.product_id else None
    if action.create_product:
        product = product_repo.create_product(
            db,
            canonical_name=str(action.canonical_name or action.product_name).strip(),
            brand=action.brand,
            category=action.category,
            specification=action.specification,
        )
        for alias in action.aliases:
            normalized = normalize_product_text(alias)
            if normalized:
                product_repo.add_alias(db, product, alias, normalized, source="owner_confirmed")
    elif product is None and action.product_name:
        # V1 确认接口本身已经是人工最终确认。升级后将历史自由文本在同一事务中
        # 解析为现有产品或创建 draft/incomplete，而不是破坏旧记账闭环。
        matched = resolve_product(db, action.product_name)
        if matched["status"] == "exact":
            product = product_repo.get_product(db, matched["matched"]["id"])
        elif matched["status"] == "not_found":
            product = product_repo.create_product(db, canonical_name=action.product_name)
        else:
            raise DomainError("商品名称匹配到多个近似产品，请先选择具体产品")
    if product is None:
        raise DomainError("产品不存在或已停用")
    product_name = product.canonical_name
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
        product_id=product.id,
    )
    return {
        "type": "record_product_purchase",
        "message": f"已记录购买 {product_name} 共 {quantity} 件。",
        "occurred_on": occurred_on,
        "product_name": product_name,
        "product_id": product.id,
        "product_lifecycle_status": product.lifecycle_status,
        "knowledge_status": product.knowledge_status,
    }


def _do_customer_fact(db: Session, customer: Customer, action, proposal) -> dict:
    fact = fact_repo.create_confirmed(
        db,
        customer_id=customer.id,
        fact_type=action.fact_type,
        display_value=action.display_value.strip(),
        normalized_value=normalize_fact_value(action.display_value),
        evidence_text=action.evidence_text.strip(),
        source_type="conversation",
        source_id=str(proposal.id),
        confidence=action.confidence,
        sensitivity_level=action.sensitivity_level,
        supersedes_id=action.supersedes_id,
    )
    return {
        "type": "upsert_customer_fact",
        "message": f"已确认客户事实：{fact.display_value}。",
        "fact_id": fact.id,
        "fact_type": fact.fact_type,
        "supersedes_id": fact.supersedes_id,
    }


def _do_delete_customer_fact(db: Session, customer: Customer, action, proposal) -> dict:
    previous, retraction = fact_repo.retract_current(
        db, customer_id=customer.id, fact_id=action.fact_id,
        evidence_text=action.evidence_text.strip(), source_id=str(proposal.id),
    )
    return {
        "type": "delete_customer_fact",
        "message": f"已撤销客户事实：{previous.display_value}。",
        "fact_id": previous.id,
        "retraction_id": retraction.id,
    }


def _do_create_product(db: Session, action) -> dict:
    product = product_repo.create_product(
        db, canonical_name=action.canonical_name, brand=action.brand,
        category=action.category, specification=action.specification,
    )
    for alias in action.aliases:
        normalized = normalize_product_text(alias)
        if normalized:
            product_repo.add_alias(db, product, alias, normalized, source="owner_confirmed")
    return {
        "type": "create_product",
        "message": f"已新增产品草稿「{product.canonical_name}」，资料待补充。",
        "product_id": product.id,
        "lifecycle_status": product.lifecycle_status,
        "knowledge_status": product.knowledge_status,
    }


def _do_merge_product(db: Session, action) -> dict:
    source, target, moved = product_repo.merge_products(
        db, action.source_product_id, action.target_product_id
    )
    source_alias = normalize_product_text(source.canonical_name)
    if source_alias:
        product_repo.add_alias(
            db, target, source.canonical_name, source_alias, source="product_merge"
        )
    return {
        "type": "merge_product",
        "message": f"已将「{source.canonical_name}」合并到「{target.canonical_name}」。",
        "source_product_id": source.id,
        "target_product_id": target.id,
        "moved_ledger_count": moved,
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
