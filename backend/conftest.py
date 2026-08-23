"""pytest 配置：保证 app 可导入，并提供隔离的内存数据库 fixture。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.config import get_settings
from app.infrastructure.models import Base
from app.main import app


@pytest.fixture(autouse=True)
def disable_paid_model_calls(monkeypatch):
    """自动测试默认禁用真实模型；需要模型的用例显式注入 MockModel。"""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    monkeypatch.setenv("ENABLE_V2_REAL_MODEL", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def db_session():
    """每个测试独立的内存 SQLite 数据库（含提示词初始化）。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = session_factory()
    from app.agent.prompt_loader import ensure_prompt_initialized

    ensure_prompt_initialized(session)
    yield session
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def client(db_session):
    """测试客户端：请求使用隔离的内存数据库。"""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
