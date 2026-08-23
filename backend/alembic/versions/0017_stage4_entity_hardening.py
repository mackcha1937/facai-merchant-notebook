"""0017：阶段4客户事实与产品实体查询/合并加固。

revision: 0017_stage4_entity_hardening
down_revision: 0016_stage3_pending_read_status

只增加阶段4需要的归属、合并指针与查询索引；不创建知识文档、
EmbeddingRecord 或 RAG 数据。
"""
from alembic import op
import sqlalchemy as sa


revision = "0017_stage4_entity_hardening"
down_revision = "0016_stage3_pending_read_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("products") as batch:
        batch.add_column(sa.Column("owner_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("merged_into_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_products_merged_into", "products", ["merged_into_id"], ["id"]
        )

    # 阶段1历史草稿均归属本 tenant 的首位 owner；无法定位 owner 时保持 NULL，
    # 不猜测跨租户身份。
    op.execute(
        """
        UPDATE products
        SET owner_id = (
            SELECT MIN(users.id) FROM users
            WHERE users.tenant_id = products.tenant_id AND users.role = 'owner'
        )
        WHERE owner_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE product_aliases
        SET normalized_alias = lower(trim(alias))
        WHERE normalized_alias IS NULL OR normalized_alias = ''
        """
    )

    op.create_index(
        "ix_customer_facts_current",
        "customer_facts",
        ["tenant_id", "customer_id", "fact_type", "confirmation_status", "valid_to"],
    )
    op.create_index(
        "ix_product_aliases_normalized",
        "product_aliases",
        ["tenant_id", "normalized_alias"],
    )
    op.create_index(
        "ix_products_entity_status",
        "products",
        ["tenant_id", "lifecycle_status", "knowledge_status"],
    )
    op.create_index("ix_products_merged_into", "products", ["merged_into_id"])


def downgrade() -> None:
    op.drop_index("ix_products_merged_into", table_name="products")
    op.drop_index("ix_products_entity_status", table_name="products")
    op.drop_index("ix_product_aliases_normalized", table_name="product_aliases")
    op.drop_index("ix_customer_facts_current", table_name="customer_facts")
    with op.batch_alter_table("products") as batch:
        batch.drop_constraint("fk_products_merged_into", type_="foreignkey")
        batch.drop_column("merged_into_id")
        batch.drop_column("owner_id")
