"""阶段1 最终整改测试：tenant 外键扫描、历史商品迁移、RBAC API、回滚一致性、跨租户父对象。"""
import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.core.rbac import require_admin, require_owner
from app.core.tenant import set_current_role, set_current_tenant_id
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
    assert c.get("/api/settings/prompt").status_code == 403
    assert c.get("/api/settings/prompt/versions").status_code == 403


def test_owner_cannot_model_check(monkeypatch):
    c = _owner_client(monkeypatch)
    assert c.post("/api/model/check").status_code == 403


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


# ---------- 六、Product 唯一约束（0014） ----------

def test_product_unique_constraint_behavior(tmp_path):
    cfg, db = _cfg(tmp_path)
    command.upgrade(cfg, "head")
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA foreign_keys=ON")

    # 唯一索引存在
    idx = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='uq_products_tenant_name'").fetchone()
    assert idx is not None, "0014 应创建 uq_products_tenant_name 部分唯一索引"

    # 准备租户2（默认只回填租户1）
    conn.execute("INSERT INTO tenants (id, display_name, status, created_at, updated_at) VALUES (2, 'B店', 'active', datetime('now'), datetime('now'))")

    # 同租户同名未删除 → 拒绝
    conn.execute("INSERT INTO products (tenant_id, canonical_name, lifecycle_status, knowledge_status, version, created_at, updated_at) VALUES (1, '面膜', 'draft', 'incomplete', 1, datetime('now'), datetime('now'))")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO products (tenant_id, canonical_name, lifecycle_status, knowledge_status, version, created_at, updated_at) VALUES (1, '面膜', 'draft', 'incomplete', 1, datetime('now'), datetime('now'))")

    # 不同租户同名 → 允许
    conn.execute("INSERT INTO products (tenant_id, canonical_name, lifecycle_status, knowledge_status, version, created_at, updated_at) VALUES (2, '面膜', 'draft', 'incomplete', 1, datetime('now'), datetime('now'))")

    # 已删除的同名 → 允许（部分索引只约束未删除行）
    conn.execute("INSERT INTO products (tenant_id, canonical_name, lifecycle_status, knowledge_status, version, created_at, updated_at, deleted_at) VALUES (1, '面膜', 'draft', 'incomplete', 1, datetime('now'), datetime('now'), datetime('now'))")
    conn.close()


# ---------- 七、验证接口与 model-status 权限 ----------

def test_stage1_status_requires_enable_flag(monkeypatch):
    from types import SimpleNamespace

    import app.api.routes.v2_stage1 as v2_stage1

    # 关闭开关 → 403，不暴露数据
    monkeypatch.setattr(v2_stage1, "get_settings", lambda: SimpleNamespace(enable_stage1_verify=False))
    c = TestClient(app)
    resp = c.get("/api/v2/stage1/status")
    assert resp.status_code == 403
    assert "未开启" in resp.json()["detail"]


def test_model_status_fail_closed_without_context(monkeypatch):
    from app.core import config as config_module

    monkeypatch.setattr(config_module.get_settings(), "local_dev_owner_enabled", False)
    set_current_role(None)
    c = TestClient(app)
    resp = c.get("/api/config/model-status")
    assert resp.status_code == 400
    assert "缺少用户上下文" in resp.json()["detail"]


# ---------- 八、0008 双数据库完整结构对比 ----------

def _snapshot_all_tables(db):
    conn = sqlite3.connect(str(db))
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()]
    snap = {}
    for t in tables:
        cols = conn.execute(f"PRAGMA table_info({t})").fetchall()
        fks = conn.execute(f"PRAGMA foreign_key_list({t})").fetchall()
        idxs = conn.execute(f"PRAGMA index_list({t})").fetchall()
        snap[t] = {
            "cols": [(c[1], c[2], c[3], c[5]) for c in cols],
            "fks": sorted((f[3], f[2], f[4]) for f in fks),
            "idxs": sorted((i[1], i[2], i[4]) for i in idxs),
        }
    conn.close()
    return snap


def test_head_downgrade_0008_full_structure_match(tmp_path):
    def make_cfg(db_path):
        cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
        cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
        cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
        return cfg

    db_a = tmp_path / "a.db"
    db_b = tmp_path / "b.db"

    # A：直接 upgrade 到 0008
    command.upgrade(make_cfg(db_a), "0008_release")
    snap_a = _snapshot_all_tables(db_a)

    # B：head 后 downgrade 到 0008
    command.upgrade(make_cfg(db_b), "head")
    command.downgrade(make_cfg(db_b), "0008_release")
    snap_b = _snapshot_all_tables(db_b)

    assert set(snap_a) == set(snap_b), f"表集合不一致：{set(snap_a) ^ set(snap_b)}"
    for t in sorted(snap_a):
        assert snap_a[t] == snap_b[t], f"表 {t} 结构不一致：\nA={snap_a[t]}\nB={snap_b[t]}"


# ---------- 九、0014 商品名 TRIM 后 product_id 保留 ----------

def test_0014_trim_preserves_product_id_and_merges(tmp_path):
    cfg, db = _cfg(tmp_path)
    command.upgrade(cfg, "0013_tenant_index_completion")
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA foreign_keys=ON")

    # 租户2 与客户（tenant_id 外键要求）
    conn.execute("INSERT INTO tenants (id, display_name, status, created_at, updated_at) VALUES (2, 'B店', 'active', datetime('now'), datetime('now'))")
    conn.execute("INSERT INTO customers (id, tenant_id, display_name) VALUES (1, 1, '小红')")
    conn.execute("INSERT INTO customers (id, tenant_id, display_name) VALUES (2, 2, '小明')")

    # 租户1：两个标准化后重名的商品（' 面霜 ' 与 '面霜'）；租户2：同名带空格商品
    cur = conn.execute("INSERT INTO products (tenant_id, canonical_name, lifecycle_status, knowledge_status, version, created_at, updated_at) VALUES (1, ' 面霜 ', 'draft', 'incomplete', 1, datetime('now'), datetime('now'))")
    p1 = cur.lastrowid
    cur = conn.execute("INSERT INTO products (tenant_id, canonical_name, lifecycle_status, knowledge_status, version, created_at, updated_at) VALUES (1, '面霜', 'draft', 'incomplete', 1, datetime('now'), datetime('now'))")
    p2 = cur.lastrowid
    cur = conn.execute("INSERT INTO products (tenant_id, canonical_name, lifecycle_status, knowledge_status, version, created_at, updated_at) VALUES (2, ' 面霜 ', 'draft', 'incomplete', 1, datetime('now'), datetime('now'))")
    p3 = cur.lastrowid

    # 账本：L1/L2 同租户重名，L3 跨租户，L4 空商品名（不应关联）
    conn.execute("INSERT INTO ledger_entries (tenant_id, customer_id, entry_type, product_name, product_id, quantity) VALUES (1, 1, 'product_purchase', ' 面霜 ', ?, 1)", (p1,))
    conn.execute("INSERT INTO ledger_entries (tenant_id, customer_id, entry_type, product_name, product_id, quantity) VALUES (1, 1, 'product_purchase', '面霜', ?, 1)", (p2,))
    conn.execute("INSERT INTO ledger_entries (tenant_id, customer_id, entry_type, product_name, product_id, quantity) VALUES (2, 2, 'product_purchase', ' 面霜 ', ?, 1)", (p3,))
    conn.execute("INSERT INTO ledger_entries (tenant_id, customer_id, entry_type, product_name, product_id, quantity) VALUES (1, 1, 'product_purchase', '   ', NULL, 1)")
    conn.commit()
    conn.close()

    command.upgrade(cfg, "head")

    conn = sqlite3.connect(str(db))
    # canonical_name 已 TRIM
    names = {r[0]: r[1] for r in conn.execute("SELECT id, canonical_name FROM products WHERE deleted_at IS NULL").fetchall()}
    assert names[p1] == "面霜"
    assert names[p3] == "面霜"
    # 同租户重名合并：仅保留最小 id（p1），p2 被删除；跨租户 p3 保留
    survivors = {r[0] for r in conn.execute("SELECT id FROM products WHERE deleted_at IS NULL").fetchall()}
    assert p1 in survivors and p2 not in survivors and p3 in survivors

    # product_name 原文保留，product_id 指向正确（trim 后合并到 p1，跨租户仍 p3，空名仍 NULL）
    rows = conn.execute("SELECT product_name, product_id, tenant_id FROM ledger_entries ORDER BY id").fetchall()
    assert rows[0] == (" 面霜 ", p1, 1), f"带空格记录原文保留且指向 p1：{rows[0]}"
    assert rows[1] == ("面霜", p1, 1), f"无空格记录合并后指向 p1：{rows[1]}"
    assert rows[2] == (" 面霜 ", p3, 2), f"跨租户记录仍指向 p3：{rows[2]}"
    assert rows[3] == ("   ", None, 1), f"空商品名不关联：{rows[3]}"
    conn.close()
