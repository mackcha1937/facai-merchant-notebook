"""0012：历史商品迁移加固（外键 + 索引 + 去重）。

revision: 0012_product_migration_hardening
down_revision: 0011_tenant_fk_completion
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_product_migration_hardening"
down_revision = "0011_tenant_fk_completion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("PRAGMA foreign_keys=OFF")

    # 1. 去重：同名同租户的 Product 草稿合并，保留最小 id
    bind.exec_driver_sql(
        """
        UPDATE ledger_entries SET product_id = (
            SELECT MIN(p.id) FROM products p
            WHERE p.tenant_id = ledger_entries.tenant_id
              AND p.canonical_name = ledger_entries.product_name
              AND p.deleted_at IS NULL
        )
        WHERE product_name IS NOT NULL AND product_name != ''
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

    # 2. product_id 外键 + 索引（batch 重建 ledger_entries）
    with op.batch_alter_table("ledger_entries") as batch:
        batch.create_foreign_key("fk_ledger_product", "products", ["product_id"], ["id"])
    op.create_index("ix_ledger_product_id", "ledger_entries", ["product_id"])


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("PRAGMA foreign_keys=OFF")
    # 删除 product_id 索引
    op.drop_index("ix_ledger_product_id", table_name="ledger_entries")
    # 明确删除 fk_ledger_product 外键（batch 重建移除）
    with op.batch_alter_table("ledger_entries", recreate="always") as batch:
        batch.drop_constraint("fk_ledger_product", type_="foreignkey")
    # 不删除 product_name 和历史 Product 草稿
