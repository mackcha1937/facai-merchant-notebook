"""服务项目数据访问。"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.models import Service


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def list_services(db: Session) -> list[Service]:
    return list(
        db.scalars(
            select(Service).where(Service.deleted_at.is_(None)).order_by(Service.id)
        ).all()
    )


def get_service(db: Session, service_id: int) -> Service | None:
    return db.scalar(
        select(Service).where(Service.id == service_id, Service.deleted_at.is_(None))
    )


def get_service_any(db: Session, service_id: int) -> Service | None:
    """含已删除，用于恢复。"""
    return db.scalar(select(Service).where(Service.id == service_id))


def find_active_service_by_name(db: Session, name: str) -> Service | None:
    return db.scalar(
        select(Service).where(
            Service.name == name, Service.deleted_at.is_(None)
        )
    )


def create_service(db: Session, name: str, status: str = "active") -> Service:
    service = Service(name=name, status=status)
    db.add(service)
    db.flush()
    return service


def soft_delete_service(db: Session, service: Service) -> None:
    service.deleted_at = _utcnow()
    db.flush()


def restore_service(db: Session, service: Service) -> None:
    service.deleted_at = None
    db.flush()
