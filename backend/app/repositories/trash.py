"""回收站数据访问：收集各类软删除数据（强制 tenant 过滤）。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tenant import get_current_tenant_id
from app.infrastructure.models import Customer, LedgerEntry, Package, Service


def list_trash(db: Session) -> list[dict]:
    tenant_id = get_current_tenant_id()
    items: list[dict] = []

    customers = db.scalars(
        select(Customer).where(
            Customer.deleted_at.is_not(None), Customer.tenant_id == tenant_id
        )
    ).all()
    for c in customers:
        items.append(
            {"type": "customer", "id": c.id, "name": c.display_name, "deleted_at": c.deleted_at}
        )

    services = db.scalars(
        select(Service).where(
            Service.deleted_at.is_not(None), Service.tenant_id == tenant_id
        )
    ).all()
    for s in services:
        items.append(
            {"type": "service", "id": s.id, "name": s.name, "deleted_at": s.deleted_at}
        )

    packages = db.scalars(
        select(Package).where(
            Package.deleted_at.is_not(None), Package.tenant_id == tenant_id
        )
    ).all()
    for p in packages:
        items.append(
            {"type": "package", "id": p.id, "name": f"套餐#{p.id}", "deleted_at": p.deleted_at}
        )

    entries = db.scalars(
        select(LedgerEntry).where(
            LedgerEntry.deleted_at.is_not(None), LedgerEntry.tenant_id == tenant_id
        )
    ).all()
    for e in entries:
        items.append(
            {"type": "ledger", "id": e.id, "name": f"记录#{e.id}", "deleted_at": e.deleted_at}
        )

    items.sort(key=lambda x: str(x["deleted_at"]), reverse=True)
    return items
