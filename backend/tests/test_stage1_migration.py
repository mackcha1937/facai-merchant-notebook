"""阶段1：Alembic 迁移测试（对独立临时库，不碰真实数据库）。"""
import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_LOCATION = str(BACKEND_ROOT / "alembic")


@pytest.fixture()
def alembic_cfg(tmp_path):
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    db_path = tmp_path / "migration_test.db"
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    cfg.set_main_option("script_location", SCRIPT_LOCATION)
    return cfg, db_path


def _tables(db_path):
    conn = sqlite3.connect(str(db_path))
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    return tables


def test_upgrade_empty_db_to_head(alembic_cfg):
    cfg, db_path = alembic_cfg
    command.upgrade(cfg, "head")
    tables = _tables(db_path)
    # V1 7 张表 + 新表
    for t in ("customers", "packages", "ledger_entries", "tenants", "users", "invites",
              "customer_facts", "products", "product_aliases", "knowledge_documents",
              "embedding_records", "conversation_threads", "recommendations", "prompt_releases"):
        assert t in tables, f"缺少表 {t}"
    assert len(tables) >= 38


def test_upgrade_then_downgrade_safe(alembic_cfg):
    cfg, db_path = alembic_cfg
    command.upgrade(cfg, "head")
    # downgrade 到 baseline（不删除 V1 表）
    command.downgrade(cfg, "0001_baseline")
    tables = _tables(db_path)
    # V1 7 张表仍在
    for t in ("customers", "customer_aliases", "services", "packages", "ledger_entries", "prompt_versions", "agent_proposals"):
        assert t in tables, f"downgrade 后 V1 表 {t} 丢失"
    # 新表已删除
    assert "tenants" not in tables


def test_default_tenant_backfill(alembic_cfg):
    cfg, db_path = alembic_cfg
    command.upgrade(cfg, "head")
    conn = sqlite3.connect(str(db_path))
    # 默认租户和 owner 存在
    tenant = conn.execute("SELECT id, display_name FROM tenants").fetchone()
    assert tenant == (1, "默认店铺")
    user = conn.execute("SELECT id, tenant_id, role FROM users").fetchone()
    assert user == (1, 1, "owner")
    conn.close()


def test_upgrade_is_idempotent(alembic_cfg):
    cfg, _ = alembic_cfg
    command.upgrade(cfg, "head")
    # 再次 upgrade 应无变化、不报错
    command.upgrade(cfg, "head")


def test_reupgrade_after_downgrade(alembic_cfg):
    cfg, db_path = alembic_cfg
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0001_baseline")
    command.upgrade(cfg, "head")
    tables = _tables(db_path)
    assert "tenants" in tables
    assert "customer_facts" in tables
