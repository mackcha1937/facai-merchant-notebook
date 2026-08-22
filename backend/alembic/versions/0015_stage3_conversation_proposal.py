"""0015：阶段3多日会话与统一 Proposal 强一致性约束。

revision: 0015_stage3_conversation_proposal
down_revision: 0014_product_unique_constraint
"""
from alembic import op
import sqlalchemy as sa


revision = "0015_stage3_conversation_proposal"
down_revision = "0014_product_unique_constraint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("conversation_threads") as batch:
        batch.create_unique_constraint(
            "uq_conversation_thread_tenant_owner", ["tenant_id", "owner_id"]
        )

    with op.batch_alter_table("conversation_sessions") as batch:
        batch.add_column(sa.Column("timezone", sa.String(length=50), nullable=False, server_default="Asia/Shanghai"))
        batch.create_unique_constraint(
            "uq_conversation_session_thread_date", ["tenant_id", "thread_id", "session_date"]
        )

    with op.batch_alter_table("messages") as batch:
        batch.add_column(sa.Column("request_id", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("read_at", sa.DateTime(), nullable=True))
        batch.create_unique_constraint("uq_messages_tenant_request", ["tenant_id", "request_id"])

    with op.batch_alter_table("agent_proposals") as batch:
        batch.add_column(sa.Column("owner_id", sa.Integer(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("thread_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("request_id", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("idempotency_key", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("confirmation_idempotency_key", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("expires_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("resolved_absolute_dates", sa.Text(), nullable=True))
        batch.add_column(sa.Column("data_version", sa.Integer(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("authority_snapshot_json", sa.Text(), nullable=True))
        batch.add_column(sa.Column("result_json", sa.Text(), nullable=True))
        batch.add_column(sa.Column("confirmed_by_device", sa.String(length=100), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
        batch.create_unique_constraint("uq_agent_proposals_tenant_request", ["tenant_id", "request_id"])
        batch.create_unique_constraint("uq_agent_proposals_tenant_idempotency", ["tenant_id", "idempotency_key"])
        batch.create_foreign_key(
            "fk_agent_proposals_thread", "conversation_threads", ["thread_id"], ["id"]
        )

    with op.batch_alter_table("message_blocks") as batch:
        batch.add_column(sa.Column("proposal_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_message_blocks_proposal", "agent_proposals", ["proposal_id"], ["id"]
        )

    with op.batch_alter_table("pending_actions") as batch:
        batch.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("resolved_at", sa.DateTime(), nullable=True))
        batch.create_unique_constraint("uq_pending_actions_tenant_proposal", ["tenant_id", "proposal_id"])
        batch.create_foreign_key(
            "fk_pending_actions_thread", "conversation_threads", ["thread_id"], ["id"]
        )
        batch.create_foreign_key(
            "fk_pending_actions_proposal", "agent_proposals", ["proposal_id"], ["id"]
        )

    with op.batch_alter_table("context_summaries") as batch:
        batch.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
        batch.create_unique_constraint("uq_context_summaries_tenant_session", ["tenant_id", "session_id"])

    op.create_index("ix_sessions_thread_date", "conversation_sessions", ["tenant_id", "thread_id", "session_date"])
    op.create_index("ix_messages_session_cursor", "messages", ["tenant_id", "session_id", "id"])
    op.create_index("ix_pending_thread_status", "pending_actions", ["tenant_id", "thread_id", "status"])
    op.create_index("ix_proposals_thread_status", "agent_proposals", ["tenant_id", "thread_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_proposals_thread_status", table_name="agent_proposals")
    op.drop_index("ix_pending_thread_status", table_name="pending_actions")
    op.drop_index("ix_messages_session_cursor", table_name="messages")
    op.drop_index("ix_sessions_thread_date", table_name="conversation_sessions")

    with op.batch_alter_table("context_summaries") as batch:
        batch.drop_constraint("uq_context_summaries_tenant_session", type_="unique")
        batch.drop_column("version")

    with op.batch_alter_table("pending_actions") as batch:
        batch.drop_constraint("fk_pending_actions_proposal", type_="foreignkey")
        batch.drop_constraint("fk_pending_actions_thread", type_="foreignkey")
        batch.drop_constraint("uq_pending_actions_tenant_proposal", type_="unique")
        batch.drop_column("resolved_at")
        batch.drop_column("updated_at")

    with op.batch_alter_table("message_blocks") as batch:
        batch.drop_constraint("fk_message_blocks_proposal", type_="foreignkey")
        batch.drop_column("proposal_id")

    with op.batch_alter_table("agent_proposals") as batch:
        batch.drop_constraint("fk_agent_proposals_thread", type_="foreignkey")
        batch.drop_constraint("uq_agent_proposals_tenant_idempotency", type_="unique")
        batch.drop_constraint("uq_agent_proposals_tenant_request", type_="unique")
        for column in (
            "updated_at", "confirmed_by_device", "result_json", "authority_snapshot_json",
            "data_version", "resolved_absolute_dates", "expires_at",
            "confirmation_idempotency_key", "idempotency_key", "request_id", "thread_id", "owner_id",
        ):
            batch.drop_column(column)

    with op.batch_alter_table("messages") as batch:
        batch.drop_constraint("uq_messages_tenant_request", type_="unique")
        batch.drop_column("read_at")
        batch.drop_column("request_id")

    with op.batch_alter_table("conversation_sessions") as batch:
        batch.drop_constraint("uq_conversation_session_thread_date", type_="unique")
        batch.drop_column("timezone")

    with op.batch_alter_table("conversation_threads") as batch:
        batch.drop_constraint("uq_conversation_thread_tenant_owner", type_="unique")
