"""账本记录用例编排。

阶段1支持手动记录：一次性服务、商品购买、手动核销（package_consumption）。
权威余额由后端根据未删除核销记录动态计算。
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.application import serializers
from app.domain.errors import DomainError, NotFoundError
from app.domain.rules import ensure_positive_int
from app.repositories import customers as customer_repo
from app.repositories import ledger as ledger_repo
from app.repositories import packages as package_repo
from app.repositories import services as service_repo
from app.schemas.ledger import LedgerEntryCreate

ALLOWED_ENTRY_TYPES = {"one_time_service", "product_purchase", "package_consumption"}


def _today() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).date().isoformat()


def list_ledger(db: Session, customer_id: int) -> list[dict]:
    customer = customer_repo.get_customer(db, customer_id)
    if customer is None:
        raise NotFoundError("客户不存在或已删除")
    return [serializers.ledger_to_dict(e) for e in ledger_repo.list_ledger_for_customer(db, customer_id)]


def create_ledger_entry(db: Session, customer_id: int, data: LedgerEntryCreate) -> dict:
    customer = customer_repo.get_customer(db, customer_id)
    if customer is None:
        raise NotFoundError("客户不存在或已删除")
    if data.entry_type not in ALLOWED_ENTRY_TYPES:
        raise DomainError("不支持的记录类型")

    quantity = ensure_positive_int(data.quantity, "数量")
    occurred_on = data.occurred_on or _today()
    service_id = data.service_id
    product_name = data.product_name
    package_id = data.package_id
    service = None
    message = None

    if data.entry_type == "one_time_service":
        if service_id is None:
            raise DomainError("一次性服务需要选择服务项目")
        service = service_repo.get_service(db, service_id)
        if service is None:
            raise NotFoundError("服务项目不存在或已删除")
        product_name = None
        message = f"已消费 {quantity} 次 {service.name} 服务。"

    elif data.entry_type == "product_purchase":
        if not product_name or not str(product_name).strip():
            raise DomainError("商品购买需要填写商品名称")
        product_name = str(product_name).strip()
        service_id = None
        message = f"已记录购买 {product_name} 共 {quantity} 件。"

    elif data.entry_type == "package_consumption":
        if package_id is None:
            raise DomainError("手动核销需要选择套餐卡")
        package = package_repo.get_package(db, package_id)
        if package is None or package.customer_id != customer_id:
            raise DomainError("套餐卡不存在或不属于该客户")
        used = package_repo.compute_used_count(db, package)
        if used + quantity > package.total_count:
            raise DomainError("余额不足，无法核销")
        service_id = package.service_id
        service = package.service
        remaining = package.total_count - used - quantity
        message = f"已累计使用 {used + quantity}/{package.total_count} 次，还剩 {remaining} 次。"

    entry = ledger_repo.create_ledger_entry(
        db,
        customer_id=customer_id,
        entry_type=data.entry_type,
        service_id=service_id,
        package_id=package_id,
        product_name=product_name,
        quantity=quantity,
        price_cents=data.price_cents,
        occurred_on=occurred_on,
    )
    if service is not None:
        entry.service = service
    serializers.save(db)

    result = serializers.ledger_to_dict(entry)
    if message is not None:
        result["message"] = message
    return result


def delete_ledger_entry(db: Session, entry_id: int) -> dict:
    entry = ledger_repo.get_ledger_entry(db, entry_id)
    if entry is None:
        raise NotFoundError("记录不存在或已删除")
    ledger_repo.soft_delete_ledger_entry(db, entry)
    serializers.save(db)
    # 权威余额由未删除核销记录动态计算，删除后自动回退
    return {"deleted": True, "id": entry_id}


def restore_ledger_entry(db: Session, entry_id: int) -> dict:
    entry = ledger_repo.get_ledger_entry_any(db, entry_id)
    if entry is None:
        raise NotFoundError("记录不存在")

    # 恢复核销记录前校验：恢复后余额不得为负
    if entry.entry_type == "package_consumption" and entry.package_id is not None:
        package = package_repo.get_package_any(db, entry.package_id)
        if package is None or package.customer_id != entry.customer_id:
            raise DomainError("关联套餐不存在，无法恢复")
        used = package_repo.compute_used_count(db, package)
        if used + entry.quantity > package.total_count:
            raise DomainError("恢复后余额不足，无法恢复该核销记录")

    ledger_repo.restore_ledger_entry(db, entry)
    serializers.save(db)
    return serializers.ledger_to_dict(entry)
