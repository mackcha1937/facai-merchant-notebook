"""阶段1 最终整改测试：tenant 外键扫描、历史商品迁移、RBAC API、回滚一致性、跨租户父对象。"""
import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.core.rbac import require_admin, require_owner
from app.core.tenant import set_current_role, set_current_tenant_id
from app.domain.errors import DomainError
from app.main import app
from app.repositories import customers as customer_repo
from app.repositories import services as service_repo

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _cfg(tmp_path):
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    db = tmp_path / "t.db"
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db}")
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return cfg, db


@pytest.fixture(autouse=True)
def _reset():
    yield
    set_current_tenant_id(None)
    set_current_role(None)


# ---------- 一、所有 tenant 表自动扫描 ----------

def test_all_tenant_tables_notnull_fk_index(tmp_path):
    cfg, db = _cfg(tmp_path)
    command.upgrade(cfg, "head")
    conn = sqlite3.connect(str(db))
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()]
    missing = []
    for t in sorted(tables):
        cols = {r[1]: r for r in conn.execute(f"PRAGMA table_info({t})").fetchall()}
        if "tenant_id" not in cols:
            continue
        # NOT NULL
        if cols["tenant_id"][3] != 1:
            missing.append(f"{t}:tenant_id 非 NOT NULL")
        # 外键
        fks = conn.execute(f"PRAGMA foreign_key_list({t})").fetchall()
        if not any(fk[2] == "tenants" and fk[3] == "tenant_id" for fk in fks):
            missing.append(f"{t}:缺 tenant 外键")
        # 索引
        idx = [r[1] for r in conn.execute(f"PRAGMA index_list({t})").fetchall()]
        if not any("tenant_id" in i for i in idx):
            missing.append(f"{t}:缺 tenant 索引")
    conn.close()
    assert missing == [], f"未通过：{missing}"


def test_no_duplicate_parent_fk(tmp_path):
    cfg, db = _cfg(tmp_path)
    command.upgrade(cfg, "head")
    conn = sqlite3.connect(str(db))
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()]
    dups = {}
    for t in tables:
        seen = {}
        for fk in conn.execute(f"PRAGMA foreign_key_list({t})").fetchall():
            key = (fk[3], fk[2])
            seen[key] = seen.get(key, 0) + 1
        d = {k: v for k, v in seen.items() if v > 1}
        if d:
            dups[t] = d
    conn.close()
    assert dups == {}, f"存在重复外键：{dups}"


# ---------- 二、历史商品迁移真实测试 ----------

def test_historical_product_migration_real(tmp_path):
    cfg, db = _cfg(tmp_path)
    command.upgrade(cfg, "0009_tenant_integrity_hardening")  # 0010 之前
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA foreign_keys=ON")
    # 0003 已创建默认租户 id=1，这里只需插入租户2
    conn.execute("INSERT INTO tenants (id, display_name, status, created_at, updated_at) VALUES (2,'B','active',datetime('now'),datetime('now'))")
    conn.execute("INSERT INTO customers (id, tenant_id, display_name) VALUES (1,1,'小红')")
    conn.execute("INSERT INTO customers (id, tenant_id, display_name) VALUES (2,2,'小明')")
    # 同名商品多条（tenant1 两条"面膜"）+ 空商品 + tenant2 一条"面膜"
    for cid, name in [(1, "面膜"), (1, "面膜"), (1, None), (2, "面膜")]:
        conn.execute(
            "INSERT INTO ledger_entries (tenant_id, customer_id, entry_type, product_name, quantity) VALUES (?,?,?,?,?)",
            (cid, cid, "product_purchase", name, 1),
        )
    conn.commit()
    conn.close()

    command.upgrade(cfg, "head")

    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA foreign_keys=ON")
    # tenant1 "面膜" 只建 1 个草稿，tenant2 "面膜" 建 1 个，空商品不迁移
    products = conn.execute("SELECT id, tenant_id, canonical_name, lifecycle_status FROM products ORDER BY id").fetchall()
    by_tenant = {}
    for pid, tid, name, status in products:
        by_tenant.setdefault(tid, []).append((name, status))
    assert len(by_tenant[1]) == 1 and by_tenant[1][0] == ("面膜", "draft")
    assert len(by_tenant[2]) == 1 and by_tenant[2][0] == ("面膜", "draft")
    # 空商品不迁移
    null_entries = conn.execute("SELECT COUNT(*) FROM ledger_entries WHERE product_name IS NULL AND product_id IS NOT NULL").fetchone()[0]
    assert null_entries == 0
    # product_id 回填 + 外键
    backfilled = conn.execute("SELECT COUNT(*) FROM ledger_entries WHERE product_name='面膜' AND product_id IS NOT NULL").fetchone()[0]
    assert backfilled == 3
    # 非法 product_id 写入失败
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE ledger_entries SET product_id=999 WHERE product_name='面膜' AND tenant_id=1")
    conn.close()


# ---------- 三、RBAC API 闭环 ----------

def _owner_client(monkeypatch):
    from app.core import config as config_module

    monkeypatch.setattr(config_module.get_settings(), "local_dev_owner_enabled", True)
    monkeypatch.setattr(config_module.get_settings(), "local_default_owner_role", "owner")
    set_current_role("owner")
    return TestClient(app)


def test_owner_cannot_read_prompt(monkeypatch):
    c = _owner_client(monkeypatch)
    assert c.get("/api/settings/prompt").status_code == 400
    assert c.get("/api/settings/prompt/versions").status_code == 400


def test_owner_cannot_model_check(monkeypatch):
    c = _owner_client(monkeypatch)
    assert c.post("/api/model/check").status_code == 400


def test_owner_can_read_model_status(monkeypatch):
    c = _owner_client(monkeypatch)
    resp = c.get("/api/config/model-status")
    assert resp.status_code == 200
    assert "api_key" not in resp.json()


def test_admin_can_read_prompt(monkeypatch):
    from app.core import config as config_module

    monkeypatch.setattr(config_module.get_settings(), "local_dev_owner_enabled", True)
    set_current_role("admin")
    c = TestClient(app)
    assert c.get("/api/settings/prompt").status_code == 200


def test_no_role_confirm_fails(monkeypatch):
    from app.core import config as config_module

    monkeypatch.setattr(config_module.get_settings(), "local_dev_owner_enabled", False)
    set_current_role(None)
    c = TestClient(app)
    assert c.post("/api/agent/interpret", json={"text": "小蓝"}).status_code == 400


# ---------- 四、回滚一致性 head -> 0008 -> head ----------

def test_head_downgrade_0008_upgrade_head(tmp_path):
    cfg, db = _cfg(tmp_path)
    command.upgrade(cfg, "head")
    conn = sqlite3.connect(str(db))
    # 0003 已创建默认租户 id=1，直接插入客户即可
    conn.execute("INSERT INTO customers (id, tenant_id, display_name) VALUES (1,1,'小红')")
    conn.commit()
    conn.close()

    command.downgrade(cfg, "0008_release")
    conn = sqlite3.connect(str(db))
    # 0008 时 customers.tenant_id 应可空（notnull=0）
    cols = {r[1]: r for r in conn.execute("PRAGMA table_info(customers)").fetchall()}
    assert cols["tenant_id"][3] == 0, "downgrade 后 tenant_id 应为可空"
    # 数据不丢
    assert conn.execute("SELECT display_name FROM customers WHERE id=1").fetchone()[0] == "小红"
    conn.close()

    command.upgrade(cfg, "head")
    conn = sqlite3.connect(str(db))
    cols = {r[1]: r for r in conn.execute("PRAGMA table_info(customers)").fetchall()}
    assert cols["tenant_id"][3] == 1, "重新 upgrade 后 tenant_id 应为 NOT NULL"
    assert conn.execute("SELECT display_name FROM customers WHERE id=1").fetchone()[0] == "小红"
    conn.close()


# ---------- 五、跨租户父对象写入 ----------

def test_cross_tenant_parent_write_rejected(db_session):
    set_current_tenant_id(1)
    svc = service_repo.create_service(db_session, "面部清洁", "active")
    cust = customer_repo.create_customer(db_session, "小红", [])
    db_session.commit()

    set_current_tenant_id(2)
    # 用租户1 的 customer/service 在租户2 创建套餐应被拒绝（客户/服务不存在于租户2）
    from app.application import package_service
    from app.schemas.package import PackageCreate

    with pytest.raises(Exception) as exc:
        package_service.create_package(db_session, cust.id, PackageCreate(service_id=svc.id, total_count=5))
    # 跨租户父对象应返回“不存在”或权限拒绝，不泄露租户1 对象存在
    assert "不存在" in str(exc.value)
