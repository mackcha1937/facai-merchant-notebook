"""套餐卡数据访问。"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.infrastructure.models import Package


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def list_packages_for_customer(db: Session, customer_id: int) -> list[Package]:
    return list(
        db.scalars(
            select(Package)
            .where(Package.customer_id == customer_id, Package.deleted_at.is_(None))
            .options(selectinload(Package.service))
            .order_by(Package.id)
        ).all()
    )


def get_package(db: Session, package_id: int) -> Package | None:
    return db.scalar(
        select(Package)
        .where(Package.id == package_id, Package.deleted_at.is_(None))
        .options(selectinload(Package.service))
    )


def get_package_any(db: Session, package_id: int) -> Package | None:
    """含已删除，用于恢复。"""
    return db.scalar(
        select(Package).where(Package.id == package_id).options(selectinload(Package.service))
    )


def create_package(
    db: Session,
    customer_id: int,
    service_id: int,
    total_count: int,
    used_count: int,
    price_cents: int | None,
    purchased_on: str | None,
) -> Package:
    package = Package(
        customer_id=customer_id,
        service_id=service_id,
        total_count=total_count,
        used_count=used_count,
        price_cents=price_cents,
        purchased_on=purchased_on,
        status="active",
    )
    db.add(package)
    db.flush()
    return package


def soft_delete_package(db: Session, package: Package) -> None:
    package.deleted_at = _utcnow()
    db.flush()


def restore_package(db: Session, package: Package) -> None:
    package.deleted_at = None
    db.flush()
