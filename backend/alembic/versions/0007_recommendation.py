"""0007：推荐相关表（只建结构 + 状态枚举，不实现推荐业务）。

revision: 0007_recommendation
down_revision: 0006_conversation
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_recommendation"
down_revision = "0006_conversation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recommendation_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("rule_type", sa.String(length=40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("conditions_json", sa.Text(), nullable=True),
        sa.Column("hard_exclusions_json", sa.Text(), nullable=True),
        sa.Column("score_config_json", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("subject_type", sa.String(length=30), nullable=True),
        sa.Column("subject_id", sa.Integer(), nullable=True),
        sa.Column("trigger_type", sa.String(length=40), nullable=False),
        sa.Column("rule_version", sa.Integer(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("evidence_snapshot", sa.Text(), nullable=True),
        sa.Column("knowledge_versions", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="new"),
        sa.Column("unread_at", sa.DateTime(), nullable=True),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("handled_at", sa.DateTime(), nullable=True),
        sa.Column("snoozed_until", sa.DateTime(), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "message_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("recommendation_id", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "follow_up_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("feedback_text", sa.Text(), nullable=True),
        sa.Column("extracted_facts_json", sa.Text(), nullable=True),
        sa.Column("next_reminder_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("follow_up_feedback")
    op.drop_table("message_drafts")
    op.drop_table("recommendations")
    op.drop_table("recommendation_rules")
