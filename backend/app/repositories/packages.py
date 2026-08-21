"""套餐卡数据访问（强制 tenant 过滤）。"""
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.tenant import get_current_tenant_id
from app.infrastructure.models import LedgerEntry, Package


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def list_packages_for_customer(db: Session, customer_id: int) -> list[Package]:
    return list(
        db.scalars(
            select(Package)
            .where(
                Package.customer_id == customer_id,
                Package.deleted_at.is_(None),
                Package.tenant_id == get_current_tenant_id(),
            )
            .options(selectinload(Package.service))
            .order_by(Package.id)
        ).all()
    )


def list_packages_for_customer_service(
    db: Session, customer_id: int, service_id: int
) -> list[Package]:
    """某客户某服务的未删除套餐卡（含各种状态，用于核销时人工选卡）。"""
    return list(
        db.scalars(
            select(Package)
            .where(
                Package.customer_id == customer_id,
                Package.service_id == service_id,
                Package.deleted_at.is_(None),
                Package.tenant_id == get_current_tenant_id(),
            )
            .options(selectinload(Package.service))
            .order_by(Package.id)
        ).all()
    )


def get_package(db: Session, package_id: int) -> Package | None:
    return db.scalar(
        select(Package)
        .where(
            Package.id == package_id,
            Package.deleted_at.is_(None),
            Package.tenant_id == get_current_tenant_id(),
        )
        .options(selectinload(Package.service))
    )


def get_package_any(db: Session, package_id: int) -> Package | None:
    """含已删除，用于恢复。"""
    return db.scalar(
        select(Package)
        .where(Package.id == package_id, Package.tenant_id == get_current_tenant_id())
        .options(selectinload(Package.service))
    )


def create_package(
    db: Session,
    customer_id: int,
    service_id: int,
    total_count: int,
    opening_used_count: int,
    price_cents: int | None,
    purchased_on: str | None,
) -> Package:
    package = Package(
        tenant_id=get_current_tenant_id(),
        customer_id=customer_id,
        service_id=service_id,
        total_count=total_count,
        opening_used_count=opening_used_count,
        price_cents=price_cents,
        purchased_on=purchased_on,
        status="active",
    )
    db.add(package)
    db.flush()
    return package


def compute_used_count(db: Session, package: Package) -> int:
    """权威累计已用 = opening_used_count + SUM(未删除的 package_consumption.quantity)。"""
    consumed = db.scalar(
        select(func.coalesce(func.sum(LedgerEntry.quantity), 0)).where(
            LedgerEntry.package_id == package.id,
            LedgerEntry.entry_type == "package_consumption",
            LedgerEntry.deleted_at.is_(None),
        )
    ) or 0
    return package.opening_used_count + consumed


def compute_used_counts(db: Session, packages: list[Package]) -> dict[int, int]:
    """批量计算多个套餐的权威累计已用，避免 N+1。"""
    if not packages:
        return {}
    ids = [p.id for p in packages]
    rows = db.execute(
        select(
            LedgerEntry.package_id,
            func.coalesce(func.sum(LedgerEntry.quantity), 0),
        )
        .where(
            LedgerEntry.package_id.in_(ids),
            LedgerEntry.entry_type == "package_consumption",
            LedgerEntry.deleted_at.is_(None),
        )
        .group_by(LedgerEntry.package_id)
    ).all()
    consumed_by_id = {package_id: total for package_id, total in rows}
    return {p.id: p.opening_used_count + consumed_by_id.get(p.id, 0) for p in packages}


def soft_delete_package(db: Session, package: Package) -> None:
    package.deleted_at = _utcnow()
    db.flush()


def restore_package(db: Session, package: Package) -> None:
    package.deleted_at = None
    db.flush()
