"""0019 只增量加固0007四表，并验证升级/降级/再升级与核心数据完整性。"""
import hashlib
import json
import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

from app.infrastructure.models import Base


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
        "knowledge_documents": "id,tenant_id,entity_type,entity_id,knowledge_version,status,confirmed,active",
        "recommendation_rules": "id,tenant_id,rule_type,version,conditions_json,status",
        "recommendations": "id,tenant_id,customer_id,subject_type,subject_id,trigger_type,rule_version,score,status",
        "message_drafts": "id,tenant_id,recommendation_id,content",
        "follow_up_feedback": "id,tenant_id,customer_id,feedback_text,status",
    }.items():
        payload[table] = conn.execute(f"SELECT {columns} FROM {table} ORDER BY id").fetchall()
    raw = json.dumps(payload, ensure_ascii=False, default=str, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest(), payload


def test_0019_reuses_existing_tables_and_roundtrip_preserves_stage1_to5_data(tmp_path):
    path = tmp_path / "stage6.db"
    cfg = config_for(path)
    command.upgrade(cfg, "0018_stage5_knowledge_rag")
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("UPDATE tenants SET display_name='虚构店' WHERE id=1")
    conn.execute("INSERT INTO customers (id,tenant_id,display_name) VALUES (1,1,'虚构顾客')")
    conn.execute("INSERT INTO services (id,tenant_id,name,status) VALUES (1,1,'面部清洁','active')")
    conn.execute("INSERT INTO packages (id,tenant_id,customer_id,service_id,total_count,opening_used_count,status) VALUES (1,1,1,1,8,2,'active')")
    conn.execute("INSERT INTO products (id,tenant_id,canonical_name,lifecycle_status,knowledge_status,version,created_at,updated_at) VALUES (1,1,'净痘修护面霜','active','complete',1,datetime('now'),datetime('now'))")
    conn.execute("INSERT INTO ledger_entries (id,tenant_id,customer_id,entry_type,product_id,product_name,quantity,occurred_on) VALUES (1,1,1,'product_purchase',1,'净痘修护面霜',1,'2026-06-01')")
    conn.execute("INSERT INTO customer_facts (id,tenant_id,customer_id,fact_type,display_value,confirmation_status,sensitivity_level,created_at,updated_at) VALUES (1,1,1,'preference','清爽','confirmed','normal',datetime('now'),datetime('now'))")
    conn.execute("INSERT INTO knowledge_documents (id,tenant_id,entity_type,entity_id,knowledge_version,text,status,confirmed,active,source_type,source_name,created_at,updated_at) VALUES (1,1,'product',1,1,'虚构知识','published',1,1,'owner_confirmed','虚构来源',datetime('now'),datetime('now'))")
    # 0007 四表中保留一组历史空壳数据，证明0019没有删表重造。
    conn.execute("INSERT INTO recommendation_rules (id,tenant_id,rule_type,version,conditions_json,status,created_at,updated_at) VALUES (1,1,'product_repurchase',1,'{}','draft',datetime('now'),datetime('now'))")
    conn.execute("INSERT INTO recommendations (id,tenant_id,customer_id,subject_type,subject_id,trigger_type,rule_version,score,status,created_at,updated_at) VALUES (1,1,1,'product',1,'product_repurchase',1,60,'new',datetime('now'),datetime('now'))")
    conn.execute("INSERT INTO message_drafts (id,tenant_id,recommendation_id,content,created_at) VALUES (1,1,1,'历史草稿',datetime('now'))")
    conn.execute("INSERT INTO follow_up_feedback (id,tenant_id,customer_id,feedback_text,status,created_at,updated_at) VALUES (1,1,1,'历史反馈','pending',datetime('now'),datetime('now'))")
    conn.commit()
    before_hash, before = snapshot(conn)
    conn.close()

    # 本用例只验证阶段6迁移兼容；后续阶段新增head后仍应停在0019断言。
    command.upgrade(cfg, "0019_stage6_recommendation_feedback")
    conn = sqlite3.connect(path)
    after_hash, after = snapshot(conn)
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "recommendation_action_audits" in tables
    assert {"generation_key", "score_breakdown_json", "data_version", "degraded", "owner_id"} <= {
        row[1] for row in conn.execute("PRAGMA table_info(recommendations)")
    }
    assert {"variant", "checksum", "copied_at"} <= {
        row[1] for row in conn.execute("PRAGMA table_info(message_drafts)")
    }
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    conn.close()

    command.downgrade(cfg, "0018_stage5_knowledge_rag")
    conn = sqlite3.connect(path)
    down_hash, down = snapshot(conn)
    assert "recommendation_action_audits" not in {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()

    command.upgrade(cfg, "0019_stage6_recommendation_feedback")
    conn = sqlite3.connect(path)
    reup_hash, reup = snapshot(conn)
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    conn.close()

    assert before == after == down == reup
    assert before_hash == after_hash == down_hash == reup_hash


def test_0019_accepts_create_all_prebuilt_empty_action_audit_table(tmp_path):
    path = tmp_path / "stage6-prebuilt.db"
    cfg = config_for(path)
    command.upgrade(cfg, "0018_stage5_knowledge_rag")
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    engine.dispose()
    conn = sqlite3.connect(path)
    assert conn.execute("SELECT count(*) FROM recommendation_action_audits").fetchone()[0] == 0
    conn.close()

    command.upgrade(cfg, "0019_stage6_recommendation_feedback")
    conn = sqlite3.connect(path)
    assert conn.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0019_stage6_recommendation_feedback"
    foreign = conn.execute("PRAGMA foreign_key_list(recommendation_action_audits)").fetchall()
    assert any(item[2] == "tenants" and item[3] == "tenant_id" for item in foreign)
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    conn.close()
