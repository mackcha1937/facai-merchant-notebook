"""系统提示词管理路由（不返回 API Key）。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.application import prompt_service
from app.core.database import get_db
from app.core.rbac import require_admin
from app.schemas.prompt import PromptSaveRequest

router = APIRouter(prefix="/api/settings/prompt", tags=["settings"])


@router.get("")
def get_prompt(db: Session = Depends(get_db)):
    require_admin()
    return prompt_service.get_current_prompt(db)


@router.get("/versions")
def list_versions(db: Session = Depends(get_db)):
    require_admin()
    return prompt_service.list_versions(db)


@router.post("/versions", status_code=201)
def save_version(data: PromptSaveRequest, db: Session = Depends(get_db)):
    require_admin()
    return prompt_service.save_version(db, data.content)


@router.post("/versions/{version_id}/activate")
def activate_version(version_id: int, db: Session = Depends(get_db)):
    require_admin()
    return prompt_service.activate_version(db, version_id)
