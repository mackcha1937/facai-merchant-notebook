"""回收站用例。"""
from sqlalchemy.orm import Session

from app.repositories import trash as trash_repo


def list_trash(db: Session) -> dict:
    return {"items": trash_repo.list_trash(db)}
