"""Proposal 确认写入用例：按当前数据库状态重新校验，事务性写入。

这是“自然语言 → 写入账本”的最终闭环。Agent 不直接写库，
所有写入都在这里由后端完成并校验。
"""
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
from app.schemas.agent import ConfirmRequest


def confirm(db: Session, proposal_id: int, data: ConfirmRequest) -> dict:
    proposal = proposal_repo.get_proposal(db, proposal_id)
    if proposal is None:
        raise NotFoundError("解析记录不存在")
    if proposal.status != "pending":
        raise DomainError("该建议已处理，不能重复确认")

    try:
        customer = _resolve_customer(db, data.customer)

        results: list[dict] = []
        for action in data.actions:
            results.append(_execute_action(db, customer, action, proposal))

        proposal_repo.set_status(db, proposal, "confirmed")
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


def _resolve_customer(db: Session, customer_data) -> Customer:
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


def _clean_aliases(aliases) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in aliases or []:
        name = str(raw).strip()
        if name and name not in seen:
            seen.add(name)
            result.append(name)
    return result


def _execute_action(db: Session, customer: Customer, action, proposal) -> dict:
    action_type = action.type
    if action_type == "create_package":
        return _do_create_package(db, customer, action, proposal)
    if action_type == "consume_service":
        return _do_consume_service(db, customer, action, proposal)
    if action_type == "record_one_time_service":
        return _do_one_time_service(db, customer, action, proposal)
    if action_type == "record_product_purchase":
        return _do_product_purchase(db, customer, action, proposal)
    if action_type == "query_customer":
        return _do_query_customer(db, customer)
    raise DomainError(f"不支持的操作类型：{action_type}")


def _do_create_package(db: Session, customer: Customer, action, proposal) -> dict:
    if action.service_id is None:
        raise DomainError("购买套餐需要选择服务项目")
    service = service_repo.get_service(db, action.service_id)
    if service is None:
        raise NotFoundError("服务项目不存在或已删除")
    if service.status != "active":
        raise DomainError("已停用或删除的服务不能建立新套餐")
    if action.total_count is None:
        raise DomainError("购买套餐需要填写总次数")
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
        occurred_on=action.purchased_on,
        original_input=proposal.original_input,
        agent_prompt_version=proposal.prompt_version,
    )
    return {
        "type": "create_package",
        "message": f"已创建套餐「{service.name}」共 {total} 次。",
        "package_id": package.id,
        "remaining_count": total,
    }


def _do_consume_service(db: Session, customer: Customer, action, proposal) -> dict:
    if action.service_id is None:
        raise DomainError("核销需要选择服务项目")
    service = service_repo.get_service(db, action.service_id)
    if service is None:
        raise NotFoundError("服务项目不存在或已删除")

    quantity = ensure_positive_int(action.quantity or 1, "核销数量")

    packages = [
        p
        for p in package_repo.list_packages_for_customer_service(db, customer.id, service.id)
        if p.status != "inactive"
    ]
    if not packages:
        raise DomainError(
            f"客户「{customer.display_name}」没有「{service.name}」的套餐，请先购买套餐或改为一次性服务"
        )

    package = None
    if action.package_id is not None:
        for p in packages:
            if p.id == action.package_id:
                package = p
                break
        if package is None:
            raise DomainError("所选套餐卡不存在或不属于该客户/服务")
    else:
        if len(packages) > 1:
            raise DomainError("该客户有多张同类套餐卡，请选择使用哪一张")
        package = packages[0]

    validate_consume_quantity(package.total_count, package.used_count, quantity)
    package.used_count += quantity

    ledger_repo.create_ledger_entry(
        db,
        customer_id=customer.id,
        entry_type="package_consumption",
        service_id=service.id,
        package_id=package.id,
        product_name=None,
        quantity=quantity,
        price_cents=None,
        occurred_on=None,
        original_input=proposal.original_input,
        agent_prompt_version=proposal.prompt_version,
    )
    remaining = package.total_count - package.used_count
    return {
        "type": "consume_service",
        "message": f"已累计使用 {package.used_count}/{package.total_count} 次，还剩 {remaining} 次。",
        "package_id": package.id,
        "remaining_count": remaining,
    }


def _do_one_time_service(db: Session, customer: Customer, action, proposal) -> dict:
    if action.service_id is None:
        raise DomainError("一次性服务需要选择服务项目")
    service = service_repo.get_service(db, action.service_id)
    if service is None:
        raise NotFoundError("服务项目不存在或已删除")
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
        occurred_on=None,
        original_input=proposal.original_input,
        agent_prompt_version=proposal.prompt_version,
    )
    return {
        "type": "record_one_time_service",
        "message": f"已消费 {quantity} 次 {service.name} 服务。",
        "service_id": service.id,
    }


def _do_product_purchase(db: Session, customer: Customer, action, proposal) -> dict:
    if not action.product_name or not str(action.product_name).strip():
        raise DomainError("商品购买需要填写商品名称")
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
        occurred_on=None,
        original_input=proposal.original_input,
        agent_prompt_version=proposal.prompt_version,
    )
    return {
        "type": "record_product_purchase",
        "message": f"已记录购买 {product_name} 共 {quantity} 件。",
        "product_name": product_name,
    }


def _do_query_customer(db: Session, customer: Customer) -> dict:
    packages = package_repo.list_packages_for_customer(db, customer.id)
    entries = ledger_repo.list_ledger_for_customer(db, customer.id)
    summary = serializers.customer_to_dict(customer)
    summary["packages"] = [serializers.package_to_dict(p) for p in packages]
    summary["ledger"] = [serializers.ledger_to_dict(e) for e in entries]
    return {
        "type": "query_customer",
        "message": f"已查询客户「{customer.display_name}」。",
        "customer": summary,
    }
