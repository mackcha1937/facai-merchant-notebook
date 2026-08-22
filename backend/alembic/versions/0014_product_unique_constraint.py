"""0014：Product 唯一约束（tenant_id + canonical_name，未删除时唯一）。

revision: 0014_product_unique_constraint
down_revision: 0013_tenant_index_completion
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_product_unique_constraint"
down_revision = "0013_tenant_index_completion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("PRAGMA foreign_keys=OFF")

    # 1. trim 标准化
    bind.exec_driver_sql(
        "UPDATE products SET canonical_name = TRIM(canonical_name) WHERE canonical_name != TRIM(canonical_name)"
    )
    # 2. 合并同 tenant 同名 Product（保留最小 id），并回填 product_id。
    #    注意：canonical_name 已被 TRIM，比较时也必须对 product_name 做 TRIM，
    #    否则 “ 面霜 ” 这类带首尾空格的历史记录会因等值比较失败而丢失 product_id。
    bind.exec_driver_sql(
        """
        UPDATE ledger_entries SET product_id = (
            SELECT MIN(p.id) FROM products p
            WHERE p.tenant_id = ledger_entries.tenant_id
              AND p.canonical_name = TRIM(ledger_entries.product_name)
              AND TRIM(ledger_entries.product_name) != ''
              AND p.deleted_at IS NULL
        )
        WHERE product_id IS NOT NULL
        """
    )
    bind.exec_driver_sql(
        """
        DELETE FROM products WHERE id IN (
            SELECT p.id FROM products p
            JOIN products p2 ON p2.tenant_id = p.tenant_id
                AND p2.canonical_name = p.canonical_name
                AND p2.deleted_at IS NULL
            WHERE p.id > p2.id AND p.deleted_at IS NULL
        )
        """
    )
    # 3. 部分唯一索引：未删除时 tenant_id + canonical_name 唯一；不同租户可同名
    op.execute(
        "CREATE UNIQUE INDEX uq_products_tenant_name ON products (tenant_id, canonical_name) WHERE deleted_at IS NULL"
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("PRAGMA foreign_keys=OFF")
    op.execute("DROP INDEX IF EXISTS uq_products_tenant_name")
