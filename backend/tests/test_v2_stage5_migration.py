"""0018 增量 Migration 往返与阶段1-4数据完整性。"""
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
        "services": "id,tenant_id,name,status,deleted_at",
        "packages": "id,tenant_id,customer_id,service_id,total_count,opening_used_count,status,deleted_at",
        "ledger_entries": "id,tenant_id,customer_id,entry_type,product_id,product_name,quantity,deleted_at",
        "customer_facts": "id,tenant_id,customer_id,fact_type,display_value,confirmation_status,valid_to,deleted_at",
        "products": "id,tenant_id,canonical_name,lifecycle_status,knowledge_status,version,deleted_at",
        "product_aliases": "id,tenant_id,product_id,alias,deleted_at",
        "agent_proposals": "id,tenant_id,original_input,parsed_json,status",
    }.items():
        payload[table] = conn.execute(f"SELECT {columns} FROM {table} ORDER BY id").fetchall()
    raw = json.dumps(payload, ensure_ascii=False, default=str, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest(), payload


def test_0018_upgrade_downgrade_reupgrade_integrity_and_existing_data(tmp_path):
    path = tmp_path / "stage5.db"
    cfg = config_for(path)
    command.upgrade(cfg, "0017_stage4_entity_hardening")
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("INSERT INTO customers (id,tenant_id,display_name) VALUES (1,1,'虚构顾客')")
    conn.execute("INSERT INTO services (id,tenant_id,name,status) VALUES (1,1,'面部清洁','active')")
    conn.execute("INSERT INTO packages (id,tenant_id,customer_id,service_id,total_count,opening_used_count,status) VALUES (1,1,1,1,8,2,'active')")
    conn.execute("INSERT INTO products (id,tenant_id,canonical_name,lifecycle_status,knowledge_status,version,created_at,updated_at) VALUES (1,1,'净痘修护面霜','active','incomplete',1,datetime('now'),datetime('now'))")
    conn.execute("INSERT INTO product_aliases (id,tenant_id,product_id,alias,normalized_alias,created_at) VALUES (1,1,1,'痘痘霜','痘痘霜',datetime('now'))")
    conn.execute("INSERT INTO ledger_entries (id,tenant_id,customer_id,entry_type,product_id,product_name,quantity) VALUES (1,1,1,'product_purchase',1,'净痘修护面霜',1)")
    conn.execute("INSERT INTO customer_facts (id,tenant_id,customer_id,fact_type,display_value,confirmation_status,sensitivity_level,created_at,updated_at) VALUES (1,1,1,'preference','清爽','confirmed','normal',datetime('now'),datetime('now'))")
    conn.execute("INSERT INTO agent_proposals (id,tenant_id,original_input,parsed_json,status,owner_id,data_version) VALUES (1,1,'历史建议','{}','cancelled',1,1)")
    conn.commit()
    before_hash, before = snapshot(conn)
    conn.close()

    command.upgrade(cfg, "head")
    conn = sqlite3.connect(path)
    after_hash, after = snapshot(conn)
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "knowledge_chunks" in tables
    assert {"confirmed", "active", "source_type", "source_name"} <= {
        row[1] for row in conn.execute("PRAGMA table_info(knowledge_documents)")
    }
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    conn.close()

    command.downgrade(cfg, "0017_stage4_entity_hardening")
    conn = sqlite3.connect(path)
    down_hash, down = snapshot(conn)
    assert "knowledge_chunks" not in {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()

    command.upgrade(cfg, "head")
    conn = sqlite3.connect(path)
    reup_hash, reup = snapshot(conn)
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    conn.close()

    assert before == after == down == reup
    assert before_hash == after_hash == down_hash == reup_hash
