"""服务项目相关路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.application import service_service
from app.core.database import get_db
from app.schemas.service import ServiceCreate, ServiceUpdate

router = APIRouter(prefix="/api/services", tags=["services"])


@router.get("")
def list_services(db: Session = Depends(get_db)):
    return service_service.list_services(db)


@router.post("", status_code=201)
def create_service(data: ServiceCreate, db: Session = Depends(get_db)):
    return service_service.create_service(db, data)


@router.patch("/{service_id}")
def update_service(service_id: int, data: ServiceUpdate, db: Session = Depends(get_db)):
    return service_service.update_service(db, service_id, data)


@router.delete("/{service_id}")
def delete_service(service_id: int, db: Session = Depends(get_db)):
    return service_service.delete_service(db, service_id)


@router.post("/{service_id}/restore")
def restore_service(service_id: int, db: Session = Depends(get_db)):
    return service_service.restore_service(db, service_id)
