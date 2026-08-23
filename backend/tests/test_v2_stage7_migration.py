"""0020 只增量加固0008治理表，并验证往返不破坏阶段1至6数据。"""
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
        "products": "id,tenant_id,canonical_name,lifecycle_status,knowledge_status,version,deleted_at",
        "recommendations": "id,tenant_id,customer_id,subject_type,subject_id,trigger_type,rule_version,score,status",
        "ai_config_drafts": "id,tenant_id,config_type,content_json,status,created_by,created_at,updated_at",
        "evaluation_runs": "id,tenant_id,status,config_snapshot_json,started_at,finished_at,created_at",
        "evaluation_case_results": "id,tenant_id,run_id,case_id,output_json,passed,created_at",
        "prompt_releases": "id,tenant_id,version,config_snapshot_json,status,published_at,rolled_back_at,created_at",
        "release_audits": "id,tenant_id,release_type,release_id,actor_id,action,before_json,after_json,created_at",
    }.items():
        payload[table] = conn.execute(f"SELECT {columns} FROM {table} ORDER BY id").fetchall()
    raw = json.dumps(payload, ensure_ascii=False, default=str, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest(), payload


def test_0020_upgrade_downgrade_reupgrade_preserves_existing_governance_and_business_data(tmp_path):
    path = tmp_path / "stage7.db"
    cfg = config_for(path)
    command.upgrade(cfg, "0019_stage6_recommendation_feedback")
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("INSERT INTO customers (id,tenant_id,display_name) VALUES (1,1,'虚构顾客')")
    conn.execute("INSERT INTO products (id,tenant_id,canonical_name,lifecycle_status,knowledge_status,version,created_at,updated_at) VALUES (1,1,'虚构面霜','active','complete',1,datetime('now'),datetime('now'))")
    conn.execute("INSERT INTO recommendations (id,tenant_id,owner_id,customer_id,subject_type,subject_id,trigger_type,rule_version,score,status,data_version,created_at,updated_at) VALUES (1,1,1,1,'product',1,'product_repurchase',1,0.8,'viewed',1,datetime('now'),datetime('now'))")
    conn.execute("INSERT INTO ai_config_drafts (id,tenant_id,config_type,content_json,status,created_by,created_at,updated_at) VALUES (1,1,'prompt','{\"version\":\"legacy\"}','blocked',1,datetime('now'),datetime('now'))")
    conn.execute("INSERT INTO evaluation_runs (id,tenant_id,status,config_snapshot_json,started_at,finished_at,created_at) VALUES (1,1,'blocked','{}',datetime('now'),datetime('now'),datetime('now'))")
    conn.execute("INSERT INTO evaluation_case_results (id,tenant_id,run_id,case_id,output_json,passed,created_at) VALUES (1,1,1,'LEGACY-001','{}',NULL,datetime('now'))")
    conn.execute("INSERT INTO prompt_releases (id,tenant_id,version,config_snapshot_json,status,created_at) VALUES (1,1,1,'{}','draft',datetime('now'))")
    conn.execute("INSERT INTO release_audits (id,tenant_id,release_type,release_id,actor_id,action,before_json,after_json,created_at) VALUES (1,1,'prompt',1,1,'legacy','{}','{}',datetime('now'))")
    conn.commit()
    before_hash, before = snapshot(conn)
    conn.close()

    command.upgrade(cfg, "head")
    conn = sqlite3.connect(path)
    after_hash, after = snapshot(conn)
    assert {"draft_id", "suite_checksum", "runner_version", "run_key"} <= {
        row[1] for row in conn.execute("PRAGMA table_info(evaluation_runs)")
    }
    assert {"category", "safety_critical", "assertion_results_json", "factual_score"} <= {
        row[1] for row in conn.execute("PRAGMA table_info(evaluation_case_results)")
    }
    assert {"source_draft_id", "evaluation_run_id", "published_by"} <= {
        row[1] for row in conn.execute("PRAGMA table_info(prompt_releases)")
    }
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    conn.close()

    command.downgrade(cfg, "0019_stage6_recommendation_feedback")
    conn = sqlite3.connect(path)
    down_hash, down = snapshot(conn)
    conn.close()

    command.upgrade(cfg, "head")
    conn = sqlite3.connect(path)
    reup_hash, reup = snapshot(conn)
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    conn.close()

    assert before == after == down == reup
    assert before_hash == after_hash == down_hash == reup_hash
