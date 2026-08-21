"""0008：AI 发布治理相关表（草稿、测评、发布、回滚、审计）。

revision: 0008_release
down_revision: 0007_recommendation
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_release"
down_revision = "0007_recommendation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_config_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("config_type", sa.String(length=40), nullable=False),
        sa.Column("content_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    # 三类发布版本（提示词 / RAG / 推荐策略）
    for name in ("prompt_releases", "rag_releases", "recommendation_releases"):
        op.create_table(
            name,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("config_snapshot_json", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
            sa.Column("published_at", sa.DateTime(), nullable=True),
            sa.Column("rolled_back_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("config_snapshot_json", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "evaluation_case_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.String(length=100), nullable=False),
        sa.Column("output_json", sa.Text(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "release_audits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("release_type", sa.String(length=40), nullable=False),
        sa.Column("release_id", sa.Integer(), nullable=True),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("before_json", sa.Text(), nullable=True),
        sa.Column("after_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "owner_ai_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("feedback_type", sa.String(length=40), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("anonymous_entity_ids", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("owner_ai_feedback")
    op.drop_table("release_audits")
    op.drop_table("evaluation_case_results")
    op.drop_table("evaluation_runs")
    op.drop_table("recommendation_releases")
    op.drop_table("rag_releases")
    op.drop_table("prompt_releases")
    op.drop_table("ai_config_drafts")
