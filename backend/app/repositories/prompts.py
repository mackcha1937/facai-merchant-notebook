"""提示词版本数据访问（强制 tenant 过滤）。"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.tenant import get_current_tenant_id
from app.infrastructure.models import PromptVersion


def count_versions(db: Session) -> int:
    return db.scalar(
        select(func.count())
        .select_from(PromptVersion)
        .where(PromptVersion.tenant_id == get_current_tenant_id())
    ) or 0


def get_active_version(db: Session) -> PromptVersion | None:
    return db.scalar(
        select(PromptVersion).where(
            PromptVersion.is_active.is_(True),
            PromptVersion.tenant_id == get_current_tenant_id(),
        )
    )


def list_versions(db: Session) -> list[PromptVersion]:
    return list(
        db.scalars(
            select(PromptVersion)
            .where(PromptVersion.tenant_id == get_current_tenant_id())
            .order_by(PromptVersion.version.desc())
        ).all()
    )


def get_version(db: Session, version_id: int) -> PromptVersion | None:
    return db.scalar(
        select(PromptVersion).where(
            PromptVersion.id == version_id,
            PromptVersion.tenant_id == get_current_tenant_id(),
        )
    )


def next_version_number(db: Session) -> int:
    max_version = db.scalar(
        select(func.max(PromptVersion.version)).where(
            PromptVersion.tenant_id == get_current_tenant_id()
        )
    ) or 0
    return max_version + 1


def create_version(
    db: Session, version: int, content: str, active: bool = False
) -> PromptVersion:
    item = PromptVersion(
        tenant_id=get_current_tenant_id(),
        version=version,
        content=content,
        is_active=active,
    )
    db.add(item)
    db.flush()
    return item


def deactivate_all(db: Session) -> None:
    for item in db.scalars(
        select(PromptVersion).where(PromptVersion.tenant_id == get_current_tenant_id())
    ).all():
        item.is_active = False
    db.flush()
