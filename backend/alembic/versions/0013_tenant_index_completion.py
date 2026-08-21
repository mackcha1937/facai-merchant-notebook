"""0013：补齐剩余 tenant 索引。

revision: 0013_tenant_index_completion
down_revision: 0012_product_migration_hardening
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_tenant_index_completion"
down_revision = "0012_product_migration_hardening"
branch_labels = None
depends_on = None

MISSING_INDEX = ["users", "invites", "embedding_records", "knowledge_documents"]


def upgrade() -> None:
    for table in MISSING_INDEX:
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])


def downgrade() -> None:
    for table in MISSING_INDEX:
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
