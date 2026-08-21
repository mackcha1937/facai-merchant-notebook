"""V2 阶段1：数据基础/Migration/权限状态接口（只读，不返回敏感信息）。"""
import sqlite3

from fastapi import APIRouter

from app.core.config import BACKEND_ROOT

router = APIRouter(prefix="/api/v2/stage1", tags=["v2-stage1"])

V1_TABLES = {"customers", "customer_aliases", "services", "packages", "ledger_entries", "prompt_versions", "agent_proposals"}


def _db():
    return sqlite3.connect(str(BACKEND_ROOT / "data" / "app.db"))


@router.get("/status")
def stage1_status():
    conn = _db()
    try:
        cur = conn.cursor()

        # migration 版本
        try:
            version = cur.execute("SELECT version_num FROM alembic_version").fetchone()
            migration_version = version[0] if version else None
        except Exception:  # noqa: BLE001
            migration_version = None

        # 所有表
        all_tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()}
        new_tables = sorted(all_tables - V1_TABLES - {"alembic_version"})

        # tenant 回填
        tenant_count = cur.execute("SELECT COUNT(*) FROM tenants").fetchone()[0]
        owner_count = cur.execute("SELECT COUNT(*) FROM users WHERE role='owner'").fetchone()[0]
        null_tenant_customers = cur.execute("SELECT COUNT(*) FROM customers WHERE tenant_id IS NULL").fetchone()[0]

        # V1 数据基线（不返回客户姓名）
        customer_count = cur.execute("SELECT COUNT(*) FROM customers WHERE deleted_at IS NULL").fetchone()[0]
        package_count = cur.execute("SELECT COUNT(*) FROM packages WHERE deleted_at IS NULL").fetchone()[0]
        ledger_count = cur.execute("SELECT COUNT(*) FROM ledger_entries WHERE deleted_at IS NULL").fetchone()[0]

        return {
            "migration_version": migration_version,
            "table_count": len(all_tables),
            "new_table_count": len(new_tables),
            "new_tables": new_tables,
            "tenant_count": tenant_count,
            "owner_count": owner_count,
            "null_tenant_customers": null_tenant_customers,
            "v1_baseline": {
                "customer_count": customer_count,
                "package_count": package_count,
                "ledger_count": ledger_count,
            },
        }
    finally:
        conn.close()
