"""客户用例编排。"""
from sqlalchemy.orm import Session

from app.application import serializers
from app.domain.errors import NotFoundError
from app.domain.rules import validate_display_name
from app.repositories import customers as customer_repo
from app.repositories import ledger as ledger_repo
from app.repositories import packages as package_repo
from app.schemas.customer import CustomerCreate, CustomerUpdate


def list_customers(db: Session, q: str | None = None) -> list[dict]:
    customers = customer_repo.list_customers(db, q)
    return [serializers.customer_to_dict(c) for c in customers]


def create_customer(db: Session, data: CustomerCreate) -> dict:
    display_name = validate_display_name(data.display_name)
    aliases = _clean_aliases(data.aliases)
    customer = customer_repo.create_customer(db, display_name, aliases)
    serializers.save(db)
    return serializers.customer_to_dict(customer)


def get_customer_detail(db: Session, customer_id: int) -> dict:
    customer = customer_repo.get_customer(db, customer_id)
    if customer is None:
        raise NotFoundError("客户不存在或已删除")
    packages = package_repo.list_packages_for_customer(db, customer_id)
    entries = ledger_repo.list_ledger_for_customer(db, customer_id)
    result = serializers.customer_to_dict(customer)
    result["packages"] = [serializers.package_to_dict(p) for p in packages]
    result["ledger"] = [serializers.ledger_to_dict(e) for e in entries]
    return result


def update_customer(db: Session, customer_id: int, data: CustomerUpdate) -> dict:
    customer = customer_repo.get_customer(db, customer_id)
    if customer is None:
        raise NotFoundError("客户不存在或已删除")
    display_name = None
    if data.display_name is not None:
        display_name = validate_display_name(data.display_name)
    aliases = _clean_aliases(data.aliases) if data.aliases is not None else None
    customer = customer_repo.update_customer(db, customer, display_name, aliases)
    serializers.save(db)
    return serializers.customer_to_dict(customer)


def delete_customer(db: Session, customer_id: int) -> dict:
    customer = customer_repo.get_customer(db, customer_id)
    if customer is None:
        raise NotFoundError("客户不存在或已删除")
    customer_repo.soft_delete_customer(db, customer)
    serializers.save(db)
    return {"deleted": True, "id": customer_id}


def restore_customer(db: Session, customer_id: int) -> dict:
    customer = customer_repo.get_customer_any(db, customer_id)
    if customer is None:
        raise NotFoundError("客户不存在")
    customer_repo.restore_customer(db, customer)
    serializers.save(db)
    return serializers.customer_to_dict(customer)


def _clean_aliases(aliases: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in aliases:
        name = str(raw).strip()
        if name and name not in seen:
            seen.add(name)
            result.append(name)
    return result
