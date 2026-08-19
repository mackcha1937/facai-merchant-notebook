"""账本记录用例编排（阶段1仅支持手动记录一次性服务与商品购买）。"""
from sqlalchemy.orm import Session

from app.application import serializers
from app.domain.errors import DomainError, NotFoundError
from app.domain.rules import ensure_positive_int
from app.repositories import customers as customer_repo
from app.repositories import ledger as ledger_repo
from app.repositories import services as service_repo
from app.schemas.ledger import LedgerEntryCreate

ALLOWED_ENTRY_TYPES = {"one_time_service", "product_purchase"}


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
        raise DomainError("不支持的记录类型（阶段1仅支持一次性服务和商品购买）")

    quantity = ensure_positive_int(data.quantity, "数量")
    service_id = data.service_id
    product_name = data.product_name
    service = None

    if data.entry_type == "one_time_service":
        if service_id is None:
            raise DomainError("一次性服务需要选择服务项目")
        service = service_repo.get_service(db, service_id)
        if service is None:
            raise NotFoundError("服务项目不存在或已删除")
        product_name = None
    else:  # product_purchase
        if not product_name or not str(product_name).strip():
            raise DomainError("商品购买需要填写商品名称")
        product_name = str(product_name).strip()
        service_id = None

    entry = ledger_repo.create_ledger_entry(
        db,
        customer_id=customer_id,
        entry_type=data.entry_type,
        service_id=service_id,
        product_name=product_name,
        quantity=quantity,
        price_cents=data.price_cents,
        occurred_on=data.occurred_on,
    )
    if service is not None:
        entry.service = service
    serializers.save(db)
    return serializers.ledger_to_dict(entry)


def delete_ledger_entry(db: Session, entry_id: int) -> dict:
    entry = ledger_repo.get_ledger_entry(db, entry_id)
    if entry is None:
        raise NotFoundError("记录不存在或已删除")
    ledger_repo.soft_delete_ledger_entry(db, entry)
    serializers.save(db)
    return {"deleted": True, "id": entry_id}


def restore_ledger_entry(db: Session, entry_id: int) -> dict:
    entry = ledger_repo.get_ledger_entry_any(db, entry_id)
    if entry is None:
        raise NotFoundError("记录不存在")
    ledger_repo.restore_ledger_entry(db, entry)
    serializers.save(db)
    return serializers.ledger_to_dict(entry)
