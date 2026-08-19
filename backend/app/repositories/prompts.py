"""提示词版本数据访问。"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure.models import PromptVersion


def count_versions(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(PromptVersion)) or 0


def get_active_version(db: Session) -> PromptVersion | None:
    return db.scalar(select(PromptVersion).where(PromptVersion.is_active.is_(True)))


def list_versions(db: Session) -> list[PromptVersion]:
    return list(
        db.scalars(select(PromptVersion).order_by(PromptVersion.version.desc())).all()
    )


def get_version(db: Session, version_id: int) -> PromptVersion | None:
    return db.scalar(select(PromptVersion).where(PromptVersion.id == version_id))


def next_version_number(db: Session) -> int:
    max_version = db.scalar(select(func.max(PromptVersion.version))) or 0
    return max_version + 1


def create_version(
    db: Session, version: int, content: str, active: bool = False
) -> PromptVersion:
    item = PromptVersion(version=version, content=content, is_active=active)
    db.add(item)
    db.flush()
    return item


def deactivate_all(db: Session) -> None:
    for item in db.scalars(select(PromptVersion)).all():
        item.is_active = False
    db.flush()
