"""服务项目数据访问（强制 tenant 过滤）。"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tenant import get_current_tenant_id
from app.infrastructure.models import Service


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def list_services(db: Session) -> list[Service]:
    return list(
        db.scalars(
            select(Service)
            .where(
                Service.deleted_at.is_(None),
                Service.tenant_id == get_current_tenant_id(),
            )
            .order_by(Service.id)
        ).all()
    )


def get_service(db: Session, service_id: int) -> Service | None:
    return db.scalar(
        select(Service).where(
            Service.id == service_id,
            Service.deleted_at.is_(None),
            Service.tenant_id == get_current_tenant_id(),
        )
    )


def get_service_any(db: Session, service_id: int) -> Service | None:
    """含已删除，用于恢复。"""
    return db.scalar(
        select(Service).where(
            Service.id == service_id, Service.tenant_id == get_current_tenant_id()
        )
    )


def find_active_service_by_name(db: Session, name: str) -> Service | None:
    return db.scalar(
        select(Service).where(
            Service.name == name,
            Service.deleted_at.is_(None),
            Service.tenant_id == get_current_tenant_id(),
        )
    )


def create_service(db: Session, name: str, status: str = "active") -> Service:
    service = Service(name=name, status=status, tenant_id=get_current_tenant_id())
    db.add(service)
    db.flush()
    return service


def soft_delete_service(db: Session, service: Service) -> None:
    service.deleted_at = _utcnow()
    db.flush()


def restore_service(db: Session, service: Service) -> None:
    service.deleted_at = None
    db.flush()
