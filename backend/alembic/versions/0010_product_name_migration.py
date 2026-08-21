"""0010：历史商品名迁移为 Product 草稿。

revision: 0010_product_name_migration
down_revision: 0009_tenant_integrity_hardening

- 保留 ledger_entries.product_name（不删除、不改名）；
- 为历史非空 product_name 按 tenant 建立 Product 草稿（draft/incomplete）；
- ledger_entries 增加可空 product_id 并回填。
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_product_name_migration"
down_revision = "0009_tenant_integrity_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ledger_entries", sa.Column("product_id", sa.Integer(), nullable=True))

    # 为每个 tenant 的每个非空 product_name 建立草稿 Product（不去重跨租户）
    op.execute(
        sa.text(
            """
            INSERT INTO products (tenant_id, canonical_name, lifecycle_status, knowledge_status, version, created_at, updated_at)
            SELECT e.tenant_id, e.product_name, 'draft', 'incomplete', 1, datetime('now'), datetime('now')
            FROM ledger_entries e
            WHERE e.product_name IS NOT NULL AND e.product_name != ''
              AND NOT EXISTS (
                  SELECT 1 FROM products p
                  WHERE p.tenant_id = e.tenant_id AND p.canonical_name = e.product_name AND p.deleted_at IS NULL
              )
            """
        )
    )
    # 回填 product_id
    op.execute(
        sa.text(
            """
            UPDATE ledger_entries SET product_id = (
                SELECT p.id FROM products p
                WHERE p.tenant_id = ledger_entries.tenant_id
                  AND p.canonical_name = ledger_entries.product_name
                  AND p.deleted_at IS NULL
            )
            WHERE product_name IS NOT NULL AND product_name != ''
            """
        )
    )


def downgrade() -> None:
    # 仅移除 product_id 列；不删除 Product 草稿（保留审计痕迹，且不删 V1 权威字段 product_name）
    with op.batch_alter_table("ledger_entries") as batch:
        batch.drop_column("product_id")
