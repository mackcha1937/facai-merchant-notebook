"""系统提示词加载与初始化。

backend/app/prompts/system_prompt.md 是首次初始化模板；
运行后的每次修改保存为 PromptVersion 记录，不覆盖模板文件。
"""
from sqlalchemy.orm import Session

from app.core.config import BACKEND_ROOT

TEMPLATE_PATH = BACKEND_ROOT / "app" / "prompts" / "system_prompt.md"


def load_template() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def ensure_prompt_initialized(db: Session) -> None:
    """若尚无任何提示词版本，用模板初始化版本 1 并激活。"""
    from app.repositories import prompts as prompt_repo

    if prompt_repo.count_versions(db) == 0:
        prompt_repo.create_version(db, 1, load_template(), active=True)
        db.commit()


def get_active_prompt(db: Session):
    """返回当前激活的 PromptVersion（若未初始化则先初始化）。"""
    from app.repositories import prompts as prompt_repo

    version = prompt_repo.get_active_version(db)
    if version is None:
        ensure_prompt_initialized(db)
        version = prompt_repo.get_active_version(db)
    return version
