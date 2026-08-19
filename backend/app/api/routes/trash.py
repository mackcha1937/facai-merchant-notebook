"""回收站相关路由。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.application import trash_service
from app.core.database import get_db

router = APIRouter(prefix="/api/trash", tags=["trash"])


@router.get("")
def list_trash(db: Session = Depends(get_db)):
    return trash_service.list_trash(db)
