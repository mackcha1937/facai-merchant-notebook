"""客户与别名数据访问（强制 tenant 过滤）。"""
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.tenant import get_current_tenant_id
from app.infrastructure.models import Customer, CustomerAlias


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def list_customers(db: Session, search: str | None = None) -> list[Customer]:
    tenant_id = get_current_tenant_id()
    stmt = (
        select(Customer)
        .where(Customer.deleted_at.is_(None), Customer.tenant_id == tenant_id)
        .options(selectinload(Customer.aliases))
    )
    if search and search.strip():
        like = f"%{search.strip()}%"
        alias_ids = select(CustomerAlias.customer_id).where(
            CustomerAlias.alias.like(like),
            CustomerAlias.deleted_at.is_(None),
        )
        stmt = stmt.where(
            or_(Customer.display_name.like(like), Customer.id.in_(alias_ids))
        )
    stmt = stmt.order_by(Customer.id)
    return list(db.scalars(stmt).all())


def get_customer(db: Session, customer_id: int) -> Customer | None:
    return db.scalar(
        select(Customer)
        .where(
            Customer.id == customer_id,
            Customer.deleted_at.is_(None),
            Customer.tenant_id == get_current_tenant_id(),
        )
        .options(selectinload(Customer.aliases))
    )


def get_customer_any(db: Session, customer_id: int) -> Customer | None:
    return db.scalar(
        select(Customer).where(
            Customer.id == customer_id, Customer.tenant_id == get_current_tenant_id()
        )
    )


def create_customer(db: Session, display_name: str, aliases: list[str]) -> Customer:
    customer = Customer(display_name=display_name, tenant_id=get_current_tenant_id())
    for alias in aliases:
        customer.aliases.append(CustomerAlias(alias=alias, tenant_id=get_current_tenant_id()))
    db.add(customer)
    db.flush()
    return customer


def update_customer(
    db: Session, customer: Customer, display_name: str | None, aliases: list[str] | None
) -> Customer:
    if display_name is not None:
        customer.display_name = display_name
    if aliases is not None:
        new_aliases: list[str] = []
        seen: set[str] = set()
        for raw in aliases:
            name = str(raw).strip()
            if name and name not in seen:
                seen.add(name)
                new_aliases.append(name)
        existing = [a for a in customer.aliases if a.deleted_at is None]
        existing_by_name = {a.alias: a for a in existing}
        for alias in existing:
            if alias.alias not in new_aliases:
                alias.deleted_at = _utcnow()
        for name in new_aliases:
            if name not in existing_by_name:
                customer.aliases.append(CustomerAlias(alias=name))
    db.flush()
    return customer


def soft_delete_customer(db: Session, customer: Customer) -> None:
    customer.deleted_at = _utcnow()
    db.flush()


def restore_customer(db: Session, customer: Customer) -> None:
    customer.deleted_at = None
    db.flush()
