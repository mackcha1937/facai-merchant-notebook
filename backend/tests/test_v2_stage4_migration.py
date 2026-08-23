"""0017 阶段4迁移升级/降级/再升级与原有数据完整性。"""
import hashlib
import json
import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def config_for(path):
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return cfg


def snapshot(conn):
    payload = {}
    for table, columns in {
        "customers": "id,tenant_id,display_name,deleted_at",
        "packages": "id,tenant_id,customer_id,service_id,total_count,opening_used_count,status,deleted_at",
        "ledger_entries": "id,tenant_id,customer_id,entry_type,product_id,product_name,quantity,deleted_at",
        "customer_facts": "id,tenant_id,customer_id,fact_type,display_value,confirmation_status,valid_to,deleted_at",
        "products": "id,tenant_id,canonical_name,lifecycle_status,knowledge_status,version,deleted_at",
        "product_aliases": "id,tenant_id,product_id,alias,deleted_at",
    }.items():
        rows = conn.execute(f"SELECT {columns} FROM {table} ORDER BY id").fetchall()
        payload[table] = rows
    raw = json.dumps(payload, ensure_ascii=False, default=str, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest(), payload


def test_0017_upgrade_downgrade_reupgrade_preserves_all_existing_rows(tmp_path):
    path = tmp_path / "stage4.db"
    cfg = config_for(path)
    command.upgrade(cfg, "0016_stage3_pending_read_status")
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("INSERT INTO customers (id,tenant_id,display_name) VALUES (1,1,'化名甲')")
    conn.execute("INSERT INTO services (id,tenant_id,name,status) VALUES (1,1,'基础护理','active')")
    conn.execute("INSERT INTO packages (id,tenant_id,customer_id,service_id,total_count,opening_used_count,status) VALUES (1,1,1,1,8,2,'active')")
    conn.execute("INSERT INTO products (id,tenant_id,canonical_name,lifecycle_status,knowledge_status,version,created_at,updated_at) VALUES (1,1,'历史面霜','draft','incomplete',1,datetime('now'),datetime('now'))")
    conn.execute("INSERT INTO product_aliases (id,tenant_id,product_id,alias,created_at) VALUES (1,1,1,' 面霜 ',datetime('now'))")
    conn.execute("INSERT INTO ledger_entries (id,tenant_id,customer_id,entry_type,product_id,product_name,quantity) VALUES (1,1,1,'product_purchase',1,'历史面霜',2)")
    conn.execute("INSERT INTO customer_facts (id,tenant_id,customer_id,fact_type,display_value,confirmation_status,sensitivity_level,created_at,updated_at) VALUES (1,1,1,'preference','清爽','confirmed','normal',datetime('now'),datetime('now'))")
    conn.commit()
    before_hash, before = snapshot(conn)
    conn.close()

    command.upgrade(cfg, "head")
    conn = sqlite3.connect(path)
    after_hash, after = snapshot(conn)
    product_columns = {row[1] for row in conn.execute("PRAGMA table_info(products)")}
    indexes = {row[1] for row in conn.execute("PRAGMA index_list(customer_facts)")}
    assert {"owner_id", "merged_into_id"} <= product_columns
    assert "ix_customer_facts_current" in indexes
    assert conn.execute("SELECT owner_id FROM products WHERE id=1").fetchone()[0] == 1
    assert conn.execute("SELECT normalized_alias FROM product_aliases WHERE id=1").fetchone()[0] == "面霜"
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    conn.close()

    command.downgrade(cfg, "0016_stage3_pending_read_status")
    conn = sqlite3.connect(path)
    down_hash, down = snapshot(conn)
    down_columns = {row[1] for row in conn.execute("PRAGMA table_info(products)")}
    assert "owner_id" not in down_columns and "merged_into_id" not in down_columns
    conn.close()

    command.upgrade(cfg, "head")
    conn = sqlite3.connect(path)
    reup_hash, reup = snapshot(conn)
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    conn.close()

    assert before == after == down == reup
    assert before_hash == after_hash == down_hash == reup_hash
