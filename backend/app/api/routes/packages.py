"""套餐卡相关路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.application import package_service
from app.core.database import get_db
from app.schemas.package import PackageCreate, PackageUpdate

router = APIRouter(prefix="/api", tags=["packages"])


@router.post("/customers/{customer_id}/packages", status_code=201)
def create_package(customer_id: int, data: PackageCreate, db: Session = Depends(get_db)):
    return package_service.create_package(db, customer_id, data)


@router.patch("/packages/{package_id}")
def update_package(package_id: int, data: PackageUpdate, db: Session = Depends(get_db)):
    return package_service.update_package(db, package_id, data)


@router.delete("/packages/{package_id}")
def delete_package(package_id: int, db: Session = Depends(get_db)):
    return package_service.delete_package(db, package_id)


@router.post("/packages/{package_id}/restore")
def restore_package(package_id: int, db: Session = Depends(get_db)):
    return package_service.restore_package(db, package_id)
