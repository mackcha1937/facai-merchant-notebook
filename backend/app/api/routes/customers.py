"""客户相关路由。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.application import customer_service
from app.core.database import get_db
from app.schemas.customer import CustomerCreate, CustomerUpdate

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("")
def list_customers(q: str | None = Query(default=None), db: Session = Depends(get_db)):
    return customer_service.list_customers(db, q)


@router.post("", status_code=201)
def create_customer(data: CustomerCreate, db: Session = Depends(get_db)):
    return customer_service.create_customer(db, data)


@router.get("/{customer_id}")
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    return customer_service.get_customer_detail(db, customer_id)


@router.patch("/{customer_id}")
def update_customer(customer_id: int, data: CustomerUpdate, db: Session = Depends(get_db)):
    return customer_service.update_customer(db, customer_id, data)


@router.delete("/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    return customer_service.delete_customer(db, customer_id)


@router.post("/{customer_id}/restore")
def restore_customer(customer_id: int, db: Session = Depends(get_db)):
    return customer_service.restore_customer(db, customer_id)
