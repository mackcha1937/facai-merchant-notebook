"""0006：会话与语音相关表（只建结构，不实现业务）。

revision: 0006_conversation
down_revision: 0005_knowledge
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_conversation"
down_revision = "0005_knowledge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversation_threads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_active_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "conversation_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("session_date", sa.String(length=20), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("message_type", sa.String(length=30), nullable=False, server_default="text"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "message_blocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("block_type", sa.String(length=40), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("state", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("data_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "entity_mentions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=30), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("surface_text", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "pending_actions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("proposal_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "context_summaries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("topics", sa.Text(), nullable=True),
        sa.Column("entity_ids", sa.Text(), nullable=True),
        sa.Column("pending_ids", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "voice_turns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=True),
        sa.Column("audio_object_ref", sa.String(length=500), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("transcript_segments", sa.Text(), nullable=True),
        sa.Column("stt_provider", sa.String(length=50), nullable=True),
        sa.Column("stt_model", sa.String(length=100), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("voice_turns")
    op.drop_table("context_summaries")
    op.drop_table("pending_actions")
    op.drop_table("entity_mentions")
    op.drop_table("message_blocks")
    op.drop_table("messages")
    op.drop_table("conversation_sessions")
    op.drop_table("conversation_threads")
