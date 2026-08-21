"""账本记录相关路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.application import ledger_service
from app.core.database import get_db
from app.core.rbac import require_owner
from app.schemas.ledger import LedgerEntryCreate

router = APIRouter(prefix="/api", tags=["ledger"])


@router.get("/customers/{customer_id}/ledger")
def list_ledger(customer_id: int, db: Session = Depends(get_db)):
    return ledger_service.list_ledger(db, customer_id)


@router.post("/customers/{customer_id}/ledger", status_code=201)
def create_ledger_entry(customer_id: int, data: LedgerEntryCreate, db: Session = Depends(get_db)):
    require_owner()
    return ledger_service.create_ledger_entry(db, customer_id, data)


@router.delete("/ledger/{entry_id}")
def delete_ledger_entry(entry_id: int, db: Session = Depends(get_db)):
    require_owner()
    return ledger_service.delete_ledger_entry(db, entry_id)


@router.post("/ledger/{entry_id}/restore")
def restore_ledger_entry(entry_id: int, db: Session = Depends(get_db)):
    require_owner()
    return ledger_service.restore_ledger_entry(db, entry_id)
