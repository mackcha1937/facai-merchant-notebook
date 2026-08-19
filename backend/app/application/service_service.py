"""服务项目用例编排。"""
from sqlalchemy.orm import Session

from app.application import serializers
from app.domain.errors import DomainError, NotFoundError
from app.domain.rules import validate_service_name
from app.repositories import services as service_repo
from app.schemas.service import ServiceCreate, ServiceUpdate

VALID_STATUSES = {"active", "inactive"}


def list_services(db: Session) -> list[dict]:
    return [serializers.service_to_dict(s) for s in service_repo.list_services(db)]


def create_service(db: Session, data: ServiceCreate) -> dict:
    name = validate_service_name(data.name)
    if service_repo.find_active_service_by_name(db, name) is not None:
        raise DomainError(f"服务名称“{name}”已存在")
    service = service_repo.create_service(db, name, "active")
    serializers.save(db)
    return serializers.service_to_dict(service)


def update_service(db: Session, service_id: int, data: ServiceUpdate) -> dict:
    service = service_repo.get_service(db, service_id)
    if service is None:
        raise NotFoundError("服务项目不存在或已删除")
    if data.name is not None:
        name = validate_service_name(data.name)
        existing = service_repo.find_active_service_by_name(db, name)
        if existing is not None and existing.id != service_id:
            raise DomainError(f"服务名称“{name}”已存在")
        service.name = name
    if data.status is not None:
        if data.status not in VALID_STATUSES:
            raise DomainError("服务状态只能是 active 或 inactive")
        service.status = data.status
    serializers.save(db)
    return serializers.service_to_dict(service)


def delete_service(db: Session, service_id: int) -> dict:
    service = service_repo.get_service(db, service_id)
    if service is None:
        raise NotFoundError("服务项目不存在或已删除")
    service_repo.soft_delete_service(db, service)
    serializers.save(db)
    return {"deleted": True, "id": service_id}


def restore_service(db: Session, service_id: int) -> dict:
    service = service_repo.get_service_any(db, service_id)
    if service is None:
        raise NotFoundError("服务项目不存在")
    service_repo.restore_service(db, service)
    serializers.save(db)
    return serializers.service_to_dict(service)
