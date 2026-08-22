"""0015 增量迁移及 V1 权威数据升级/降级/再升级一致性。"""
import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def cfg_for(path):
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return cfg


def snapshot(conn):
    counts = {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("customers", "packages", "ledger_entries")
    }
    rows = conn.execute(
        "SELECT p.id,p.total_count,p.opening_used_count,COALESCE(SUM(CASE WHEN l.entry_type='package_consumption' AND l.deleted_at IS NULL THEN l.quantity ELSE 0 END),0) "
        "FROM packages p LEFT JOIN ledger_entries l ON l.package_id=p.id GROUP BY p.id ORDER BY p.id"
    ).fetchall()
    counts["remaining"] = [(pid, total - opening - consumed) for pid, total, opening, consumed in rows]
    return counts


def test_0015_upgrade_downgrade_reupgrade_preserves_v1_data(tmp_path):
    path = tmp_path / "stage3.db"
    cfg = cfg_for(path)
    command.upgrade(cfg, "0014_product_unique_constraint")
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("INSERT INTO customers (id,tenant_id,display_name) VALUES (1,1,'化名甲')")
    conn.execute("INSERT INTO services (id,tenant_id,name,status) VALUES (1,1,'基础护理','active')")
    conn.execute("INSERT INTO packages (id,tenant_id,customer_id,service_id,total_count,opening_used_count,status) VALUES (1,1,1,1,8,2,'active')")
    conn.execute("INSERT INTO ledger_entries (tenant_id,customer_id,entry_type,package_id,service_id,quantity) VALUES (1,1,'package_consumption',1,1,2)")
    conn.commit()
    before = snapshot(conn)
    conn.close()

    command.upgrade(cfg, "head")
    conn = sqlite3.connect(path)
    after_upgrade = snapshot(conn)
    proposal_cols = {row[1] for row in conn.execute("PRAGMA table_info(agent_proposals)")}
    assert {"request_id", "idempotency_key", "expires_at", "resolved_absolute_dates", "data_version"} <= proposal_cols
    conn.close()

    command.downgrade(cfg, "0014_product_unique_constraint")
    conn = sqlite3.connect(path)
    after_down = snapshot(conn)
    conn.close()

    command.upgrade(cfg, "head")
    conn = sqlite3.connect(path)
    after_reupgrade = snapshot(conn)
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    conn.close()
    assert before == after_upgrade == after_down == after_reupgrade
