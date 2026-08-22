"""V2 阶段1：数据基础/Migration/权限状态接口（只读，不返回敏感信息）。

受 ENABLE_STAGE1_VERIFY 开关保护，默认关闭，仅开发环境显式开启。
"""
import sqlite3

from fastapi import APIRouter, HTTPException

from app.core.config import BACKEND_ROOT, get_settings

router = APIRouter(prefix="/api/v2/stage1", tags=["v2-stage1"])

V1_TABLES = {"customers", "customer_aliases", "services", "packages", "ledger_entries", "prompt_versions", "agent_proposals"}


def _db():
    return sqlite3.connect(str(BACKEND_ROOT / "data" / "app.db"))


@router.get("/status")
def stage1_status():
    settings = get_settings()
    if not settings.enable_stage1_verify:
        raise HTTPException(status_code=403, detail="阶段1验证接口未开启（ENABLE_STAGE1_VERIFY=false）")
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

        # tenant 完整性检测（自动扫描）
        tenant_tables = []
        missing_fk = []
        duplicate_fk = []
        for t in sorted(all_tables):
            cols = {r[1]: r for r in cur.execute(f"PRAGMA table_info({t})").fetchall()}
            if "tenant_id" not in cols:
                continue
            tenant_tables.append(t)
            fks = cur.execute(f"PRAGMA foreign_key_list({t})").fetchall()
            if not any(fk[2] == "tenants" and fk[3] == "tenant_id" for fk in fks):
                missing_fk.append(t)
            seen = {}
            for fk in fks:
                key = (fk[3], fk[2])
                seen[key] = seen.get(key, 0) + 1
            if any(v > 1 for v in seen.values()):
                duplicate_fk.append(t)
        cur.execute("PRAGMA foreign_keys=ON")
        fk_check = cur.execute("PRAGMA foreign_key_check").fetchall()

        # Product 唯一约束（0014）：tenant_id + canonical_name 未删除时唯一
        product_unique_index = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='uq_products_tenant_name'"
        ).fetchone()
        duplicate_active_products = cur.execute(
            "SELECT COUNT(*) FROM (SELECT 1 FROM products WHERE deleted_at IS NULL "
            "GROUP BY tenant_id, canonical_name HAVING COUNT(*) > 1)"
        ).fetchone()[0]

        return {
            "migration_version": migration_version,
            "table_count": len(all_tables),
            "new_table_count": len(new_tables),
            "new_tables": new_tables,
            "tenant_count": tenant_count,
            "owner_count": owner_count,
            "null_tenant_customers": null_tenant_customers,
            "product_draft_count": cur.execute("SELECT COUNT(*) FROM products WHERE lifecycle_status='draft'").fetchone()[0],
            "ledger_product_backfill": cur.execute("SELECT COUNT(*) FROM ledger_entries WHERE product_id IS NOT NULL").fetchone()[0],
            "tenant_table_count": len(tenant_tables),
            "missing_tenant_fk": missing_fk,
            "duplicate_fk": duplicate_fk,
            "fk_check_errors": len(fk_check),
            "product_unique_constraint": product_unique_index is not None,
            "duplicate_active_products": duplicate_active_products,
            "v1_baseline": {
                "customer_count": customer_count,
                "package_count": package_count,
                "ledger_count": ledger_count,
            },
        }
    finally:
        conn.close()
