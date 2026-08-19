"""SQLite 连接与会话管理。"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import BACKEND_ROOT, get_settings

_engine = None
_session_factory = None


def _ensure_data_dir() -> None:
    data_dir = BACKEND_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)


def get_engine():
    global _engine
    if _engine is None:
        _ensure_data_dir()
        settings = get_settings()
        _engine = create_engine(
            settings.effective_database_url,
            connect_args={"check_same_thread": False},
        )
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return _session_factory


def get_db():
    """FastAPI 依赖：每个请求一个 Session。"""
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """创建所有表（阶段1开始使用）。"""
    from app.infrastructure import models  # noqa: F401

    models.Base.metadata.create_all(bind=get_engine())


def check_database_connection() -> tuple[bool, str]:
    """执行最小 SQL 探测，返回 (是否成功, 信息)。"""
    try:
        _ensure_data_dir()
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "ok"
    except Exception as exc:  # noqa: BLE001 - 仅做连通性探测
        return False, str(exc)
