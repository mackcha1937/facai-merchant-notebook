"""0016：PendingAction 跨设备共享阅读状态。

revision: 0016_stage3_pending_read_status
down_revision: 0015_stage3_conversation_proposal
"""
from alembic import op
import sqlalchemy as sa


revision = "0016_stage3_pending_read_status"
down_revision = "0015_stage3_conversation_proposal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("pending_actions")}
    if "read_at" not in columns:
        with op.batch_alter_table("pending_actions") as batch:
            batch.add_column(sa.Column("read_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("pending_actions")}
    if "read_at" in columns:
        with op.batch_alter_table("pending_actions") as batch:
            batch.drop_column("read_at")
