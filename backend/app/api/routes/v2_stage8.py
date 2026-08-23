"""阶段8完整联调与最终本地验收状态API。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.application import stage8_service
from app.core.database import get_db


router = APIRouter(prefix="/api", tags=["v2-stage8"])


@router.get("/v2-stage8/status")
def stage8_status(db: Session = Depends(get_db)):
    return stage8_service.status(db)
