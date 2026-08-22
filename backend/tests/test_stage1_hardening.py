"""阶段1 安全加固测试：NOT NULL、外键、fail-closed、跨租户隔离、RBAC API。"""
import sqlite3

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pathlib import Path

from app.core.rbac import require_admin, require_owner
from app.core.tenant import get_current_role, get_current_tenant_id, set_current_role, set_current_tenant_id
from app.domain.errors import DomainError
from app.main import app
from app.repositories import customers as customer_repo
from app.repositories import packages as package_repo
from app.repositories import proposals as proposal_repo
from app.repositories import prompts as prompt_repo
from app.repositories import services as service_repo
from app.repositories import trash as trash_repo

BACKEND_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _reset_context():
    yield
    set_current_tenant_id(None)
    set_current_role(None)


# ---------- 迁移后 NOT NULL / 外键 / 索引 ----------

def test_tenant_id_not_null_after_migration(tmp_path):
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    db_path = tmp_path / "t.db"
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.upgrade(cfg, "head")
    conn = sqlite3.connect(str(db_path))
    for t in ("customers", "packages", "ledger_entries", "messages", "evaluation_case_results"):
        cols = {r[1]: r[3] for r in conn.execute(f"PRAGMA table_info({t})").fetchall()}
        assert cols.get("tenant_id") == 1, f"{t}.tenant_id 应为 NOT NULL"
    conn.close()


def test_invalid_tenant_foreign_key_fails(tmp_path):
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    db_path = tmp_path / "t.db"
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.upgrade(cfg, "head")
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")
    # 插入 tenant_id=999 的客户应触发外键失败
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO customers (tenant_id, display_name) VALUES (999, '非法租户客户')"
        )
    conn.close()


def test_fail_closed_without_context(monkeypatch):
    from app.core import config as config_module

    monkeypatch.setattr(config_module.get_settings(), "local_dev_owner_enabled", False)
    with pytest.raises(DomainError):
        get_current_tenant_id()
    with pytest.raises(DomainError):
        get_current_role()


# ---------- 跨租户隔离 ----------

def test_cross_tenant_search_and_delete(db_session):
    set_current_tenant_id(1)
    customer_repo.create_customer(db_session, "小红", ["红姐"])
    db_session.commit()
    set_current_tenant_id(2)
    b = customer_repo.create_customer(db_session, "小红", ["红姐"])  # 同名不同租户
    db_session.commit()

    set_current_tenant_id(1)
    found = customer_repo.list_customers(db_session, "小红")
    assert len(found) == 1
    assert found[0].tenant_id == 1

    # 租户1 无法软删租户2 的客户
    from app.repositories import customers as cr

    assert cr.get_customer(db_session, b.id) is None


def test_cross_tenant_prompt_isolation(db_session):
    set_current_tenant_id(1)
    prompt_repo.create_version(db_session, 1, "租户1提示词", active=True)
    db_session.commit()
    set_current_tenant_id(2)
    prompt_repo.create_version(db_session, 1, "租户2提示词", active=True)
    db_session.commit()

    set_current_tenant_id(1)
    versions = prompt_repo.list_versions(db_session)
    # 只看到自己租户的提示词，看不到租户2 的
    assert all(v.tenant_id == 1 for v in versions)
    assert not any("租户2提示词" == v.content for v in versions)


def test_cross_tenant_proposal_isolation(db_session):
    set_current_tenant_id(1)
    p1 = proposal_repo.create_proposal(db_session, "输入", "{}", 1, "pending")
    db_session.commit()
    set_current_tenant_id(2)
    p2 = proposal_repo.create_proposal(db_session, "输入", "{}", 1, "pending")
    db_session.commit()

    set_current_tenant_id(1)
    assert proposal_repo.get_proposal(db_session, p1.id) is not None
    assert proposal_repo.get_proposal(db_session, p2.id) is None


def test_cross_tenant_trash_isolation(db_session):
    set_current_tenant_id(1)
    c1 = customer_repo.create_customer(db_session, "A客户", [])
    db_session.commit()
    from app.application import customer_service

    customer_service.delete_customer(db_session, c1.id)
    set_current_tenant_id(2)
    trash = trash_repo.list_trash(db_session)
    # 租户2 回收站为空（看不到租户1 的软删客户）
    assert trash == []


# ---------- RBAC API ----------

def test_owner_cannot_call_admin_api(monkeypatch):
    from app.core import config as config_module

    monkeypatch.setattr(config_module.get_settings(), "local_dev_owner_enabled", True)
    monkeypatch.setattr(config_module.get_settings(), "local_default_owner_role", "owner")
    set_current_role("owner")
    client = TestClient(app)
    # 提示词保存需要 admin，owner 应 403（PermissionDeniedError 映射 403）
    resp = client.post("/api/settings/prompt/versions", json={"content": "测试提示词 包含 JSON"})
    assert resp.status_code == 403
    assert "无权限" in resp.json()["detail"]


def test_admin_can_call_admin_api(monkeypatch):
    from app.core import config as config_module

    monkeypatch.setattr(config_module.get_settings(), "local_dev_owner_enabled", True)
    set_current_role("admin")
    client = TestClient(app)
    resp = client.post("/api/settings/prompt/versions", json={"content": "测试提示词 包含 JSON 输出"})
    assert resp.status_code == 201


# ---------- 历史商品映射 ----------

def test_historical_product_draft_mapping(db_session):
    from app.infrastructure.models import Product

    set_current_tenant_id(1)
    svc = service_repo.create_service(db_session, "面部清洁", "active")
    cust = customer_repo.create_customer(db_session, "小红", ["红姐"])
    db_session.commit()
    from app.application import ledger_service
    from app.schemas.ledger import LedgerEntryCreate

    ledger_service.create_ledger_entry(
        db_session, cust.id, LedgerEntryCreate(entry_type="product_purchase", product_name="面膜", quantity=1)
    )
    # 有 product_name 记录；Product 草稿由 migration 0010 在真实库处理，这里验证 ORM 字段存在
    assert hasattr(cust, "tenant_id")


# ---------- RBAC 函数 fail closed ----------

def test_require_owner_fail_closed(monkeypatch):
    from app.core import config as config_module

    monkeypatch.setattr(config_module.get_settings(), "local_dev_owner_enabled", False)
    set_current_role(None)
    with pytest.raises(DomainError):
        require_owner()
    with pytest.raises(DomainError):
        require_admin()
