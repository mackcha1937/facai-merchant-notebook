"""提示词管理用例。"""
import json

from sqlalchemy.orm import Session

from app.agent.prompt_loader import get_active_prompt
from app.application import serializers
from app.core.config import get_settings
from app.domain.errors import DomainError, NotFoundError
from app.repositories import prompts as prompt_repo


def _version_to_dict(v) -> dict:
    return {
        "id": v.id,
        "version": v.version,
        "content": v.content,
        "created_at": v.created_at,
        "is_active": v.is_active,
    }


def get_current_prompt(db: Session) -> dict:
    v = get_active_prompt(db)
    return {
        "id": v.id,
        "version": v.version,
        "content": v.content,
        "created_at": v.created_at,
        "is_active": True,
        "model_id": get_settings().deepseek_model_id,
    }


def list_versions(db: Session) -> list[dict]:
    return [_version_to_dict(v) for v in prompt_repo.list_versions(db)]


def save_version(db: Session, content: str) -> dict:
    content = (content or "").strip()
    if not content:
        raise DomainError("提示词内容不能为空")
    if "JSON" not in content:
        raise DomainError("提示词需要包含 JSON 输出结构说明（请保留输出 JSON 的指令）")

    number = prompt_repo.next_version_number(db)
    version = prompt_repo.create_version(db, number, content, active=False)
    serializers.save(db)
    return _version_to_dict(version)


def activate_version(db: Session, version_id: int) -> dict:
    version = prompt_repo.get_version(db, version_id)
    if version is None:
        raise NotFoundError("提示词版本不存在")
    prompt_repo.deactivate_all(db)
    version.is_active = True
    serializers.save(db)
    return _version_to_dict(version)
