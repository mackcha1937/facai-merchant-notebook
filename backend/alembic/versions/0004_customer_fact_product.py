"""0004：CustomerFact / Product / ProductAlias。

revision: 0004_customer_fact_product
down_revision: 0003_tenant_id_backfill
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_customer_fact_product"
down_revision = "0003_tenant_id_backfill"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_facts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("fact_type", sa.String(length=50), nullable=False),
        sa.Column("display_value", sa.String(length=500), nullable=False),
        sa.Column("normalized_value", sa.String(length=500), nullable=True),
        sa.Column("evidence_text", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=30), nullable=True),
        sa.Column("source_id", sa.String(length=100), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("confirmation_status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("sensitivity_level", sa.String(length=20), nullable=False, server_default="normal"),
        sa.Column("valid_from", sa.DateTime(), nullable=True),
        sa.Column("valid_to", sa.DateTime(), nullable=True),
        sa.Column("supersedes_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("canonical_name", sa.String(length=200), nullable=False),
        sa.Column("brand", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("specification", sa.String(length=100), nullable=True),
        sa.Column("lifecycle_status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("knowledge_status", sa.String(length=30), nullable=False, server_default="incomplete"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "product_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(length=200), nullable=False),
        sa.Column("normalized_alias", sa.String(length=200), nullable=True),
        sa.Column("source", sa.String(length=30), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("product_aliases")
    op.drop_table("products")
    op.drop_table("customer_facts")
