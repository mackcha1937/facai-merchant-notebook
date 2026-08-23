"""0019：阶段6推荐、话术和反馈增量加固。

revision: 0019_stage6_recommendation_feedback
down_revision: 0018_stage5_knowledge_rag

复用 0007 已创建的 recommendation_rules、recommendations、message_drafts、
follow_up_feedback；只增加阶段6运行所需字段、约束、索引和动作审计表。
"""
from alembic import op
import sqlalchemy as sa


revision = "0019_stage6_recommendation_feedback"
down_revision = "0018_stage5_knowledge_rag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {item["name"] for item in inspector.get_columns("recommendation_rules")}
    unique_names = {item.get("name") for item in inspector.get_unique_constraints("recommendation_rules")}
    with op.batch_alter_table("recommendation_rules") as batch:
        if "policy_version" not in columns:
            batch.add_column(sa.Column("policy_version", sa.String(length=50), nullable=False, server_default="stage6-sql-v1"))
        if "cooldown_days" not in columns:
            batch.add_column(sa.Column("cooldown_days", sa.Integer(), nullable=False, server_default="7"))
        if "priority" not in columns:
            batch.add_column(sa.Column("priority", sa.Integer(), nullable=False, server_default="0"))
        if "published_at" not in columns:
            batch.add_column(sa.Column("published_at", sa.DateTime(), nullable=True))
        if "created_by" not in columns:
            batch.add_column(sa.Column("created_by", sa.Integer(), nullable=True))
        if "uq_recommendation_rules_tenant_type_version" not in unique_names:
            batch.create_unique_constraint("uq_recommendation_rules_tenant_type_version", ["tenant_id", "rule_type", "version"])

    inspector = sa.inspect(bind)
    columns = {item["name"] for item in inspector.get_columns("recommendations")}
    unique_names = {item.get("name") for item in inspector.get_unique_constraints("recommendations")}
    foreign_names = {item.get("name") for item in inspector.get_foreign_keys("recommendations")}
    with op.batch_alter_table("recommendations") as batch:
        additions = (
            ("owner_id", sa.Column("owner_id", sa.Integer(), nullable=False, server_default="1")),
            ("rule_id", sa.Column("rule_id", sa.Integer(), nullable=True)),
            ("policy_version", sa.Column("policy_version", sa.String(length=50), nullable=True)),
            ("generation_date", sa.Column("generation_date", sa.String(length=20), nullable=True)),
            ("generation_key", sa.Column("generation_key", sa.String(length=128), nullable=True)),
            ("score_breakdown_json", sa.Column("score_breakdown_json", sa.Text(), nullable=True)),
            ("reason", sa.Column("reason", sa.Text(), nullable=True)),
            ("suggested_action", sa.Column("suggested_action", sa.Text(), nullable=True)),
            ("degraded", sa.Column("degraded", sa.Boolean(), nullable=False, server_default=sa.false())),
            ("degraded_reason", sa.Column("degraded_reason", sa.String(length=100), nullable=True)),
            ("risk_flags_json", sa.Column("risk_flags_json", sa.Text(), nullable=True)),
            ("content_checksum", sa.Column("content_checksum", sa.String(length=64), nullable=True)),
            ("data_version", sa.Column("data_version", sa.Integer(), nullable=False, server_default="1")),
            ("contacted_at", sa.Column("contacted_at", sa.DateTime(), nullable=True)),
        )
        for name, column in additions:
            if name not in columns:
                batch.add_column(column)
        if "fk_recommendations_rule" not in foreign_names:
            batch.create_foreign_key("fk_recommendations_rule", "recommendation_rules", ["rule_id"], ["id"])
        if "uq_recommendations_tenant_generation_key" not in unique_names:
            batch.create_unique_constraint("uq_recommendations_tenant_generation_key", ["tenant_id", "generation_key"])
    index_names = {item["name"] for item in sa.inspect(bind).get_indexes("recommendations")}
    if "ix_recommendations_today_owner" not in index_names:
        op.create_index("ix_recommendations_today_owner", "recommendations", ["tenant_id", "owner_id", "generation_date", "status", "score"])
    if "ix_recommendations_duplicate_guard" not in index_names:
        op.create_index("ix_recommendations_duplicate_guard", "recommendations", ["tenant_id", "customer_id", "trigger_type", "subject_type", "subject_id", "status"])

    inspector = sa.inspect(bind)
    columns = {item["name"] for item in inspector.get_columns("message_drafts")}
    foreign_tables = {item.get("referred_table") for item in inspector.get_foreign_keys("message_drafts")}
    with op.batch_alter_table("message_drafts") as batch:
        additions = (
            ("variant", sa.Column("variant", sa.String(length=30), nullable=False, server_default="standard")),
            ("checksum", sa.Column("checksum", sa.String(length=64), nullable=True)),
            ("copied_at", sa.Column("copied_at", sa.DateTime(), nullable=True)),
            ("data_version", sa.Column("data_version", sa.Integer(), nullable=False, server_default="1")),
            ("updated_at", sa.Column("updated_at", sa.DateTime(), nullable=True)),
        )
        for name, column in additions:
            if name not in columns:
                batch.add_column(column)
        if "recommendations" not in foreign_tables:
            batch.create_foreign_key("fk_message_drafts_recommendation", "recommendations", ["recommendation_id"], ["id"])
    index_names = {item["name"] for item in sa.inspect(bind).get_indexes("message_drafts")}
    if "ix_message_drafts_recommendation_variant" not in index_names:
        op.create_index("ix_message_drafts_recommendation_variant", "message_drafts", ["tenant_id", "recommendation_id", "variant"])

    inspector = sa.inspect(bind)
    columns = {item["name"] for item in inspector.get_columns("follow_up_feedback")}
    unique_names = {item.get("name") for item in inspector.get_unique_constraints("follow_up_feedback")}
    foreign_tables = {item.get("referred_table") for item in inspector.get_foreign_keys("follow_up_feedback")}
    with op.batch_alter_table("follow_up_feedback") as batch:
        additions = (
            ("recommendation_id", sa.Column("recommendation_id", sa.Integer(), nullable=True)),
            ("owner_id", sa.Column("owner_id", sa.Integer(), nullable=False, server_default="1")),
            ("action_type", sa.Column("action_type", sa.String(length=40), nullable=False, server_default="note")),
            ("proposal_id", sa.Column("proposal_id", sa.Integer(), nullable=True)),
            ("anonymous_context_json", sa.Column("anonymous_context_json", sa.Text(), nullable=True)),
            ("evidence_checksum", sa.Column("evidence_checksum", sa.String(length=64), nullable=True)),
            ("rule_version", sa.Column("rule_version", sa.Integer(), nullable=True)),
            ("idempotency_key", sa.Column("idempotency_key", sa.String(length=128), nullable=True)),
            ("data_version", sa.Column("data_version", sa.Integer(), nullable=False, server_default="1")),
        )
        for name, column in additions:
            if name not in columns:
                batch.add_column(column)
        if "recommendations" not in foreign_tables:
            batch.create_foreign_key("fk_follow_up_feedback_recommendation", "recommendations", ["recommendation_id"], ["id"])
        if "agent_proposals" not in foreign_tables:
            batch.create_foreign_key("fk_follow_up_feedback_proposal", "agent_proposals", ["proposal_id"], ["id"])
        if "uq_follow_up_feedback_tenant_idempotency" not in unique_names:
            batch.create_unique_constraint("uq_follow_up_feedback_tenant_idempotency", ["tenant_id", "idempotency_key"])
    index_names = {item["name"] for item in sa.inspect(bind).get_indexes("follow_up_feedback")}
    if "ix_follow_up_feedback_recommendation" not in index_names:
        op.create_index("ix_follow_up_feedback_recommendation", "follow_up_feedback", ["tenant_id", "recommendation_id", "created_at"])

    inspector = sa.inspect(bind)
    if not inspector.has_table("recommendation_action_audits"):
        op.create_table(
            "recommendation_action_audits",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("recommendation_id", sa.Integer(), nullable=False),
            sa.Column("action_type", sa.String(length=40), nullable=False),
            sa.Column("idempotency_key", sa.String(length=128), nullable=False),
            sa.Column("before_json", sa.Text(), nullable=True),
            sa.Column("after_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_recommendation_audits_tenant"),
            sa.ForeignKeyConstraint(["recommendation_id"], ["recommendations.id"], name="fk_recommendation_audits_recommendation"),
            sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_recommendation_audits_tenant_idempotency"),
        )
    else:
        foreign_tables = {item.get("referred_table") for item in inspector.get_foreign_keys("recommendation_action_audits")}
        unique_names = {item.get("name") for item in inspector.get_unique_constraints("recommendation_action_audits")}
        with op.batch_alter_table("recommendation_action_audits") as batch:
            if "tenants" not in foreign_tables:
                batch.create_foreign_key("fk_recommendation_audits_tenant", "tenants", ["tenant_id"], ["id"])
            if "recommendations" not in foreign_tables:
                batch.create_foreign_key("fk_recommendation_audits_recommendation", "recommendations", ["recommendation_id"], ["id"])
            if "uq_recommendation_audits_tenant_idempotency" not in unique_names:
                batch.create_unique_constraint("uq_recommendation_audits_tenant_idempotency", ["tenant_id", "idempotency_key"])
    index_names = {item["name"] for item in sa.inspect(bind).get_indexes("recommendation_action_audits")}
    if "ix_recommendation_action_audits_tenant_id_recommendation" not in index_names:
        op.create_index("ix_recommendation_action_audits_tenant_id_recommendation", "recommendation_action_audits", ["tenant_id", "recommendation_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_recommendation_action_audits_tenant_id_recommendation", table_name="recommendation_action_audits")
    op.drop_table("recommendation_action_audits")

    op.drop_index("ix_follow_up_feedback_recommendation", table_name="follow_up_feedback")
    with op.batch_alter_table("follow_up_feedback") as batch:
        batch.drop_constraint("uq_follow_up_feedback_tenant_idempotency", type_="unique")
        batch.drop_constraint("fk_follow_up_feedback_proposal", type_="foreignkey")
        batch.drop_constraint("fk_follow_up_feedback_recommendation", type_="foreignkey")
        for column in ("data_version", "idempotency_key", "rule_version", "evidence_checksum", "anonymous_context_json", "proposal_id", "action_type", "owner_id", "recommendation_id"):
            batch.drop_column(column)

    op.drop_index("ix_message_drafts_recommendation_variant", table_name="message_drafts")
    with op.batch_alter_table("message_drafts") as batch:
        batch.drop_constraint("fk_message_drafts_recommendation", type_="foreignkey")
        for column in ("updated_at", "data_version", "copied_at", "checksum", "variant"):
            batch.drop_column(column)

    op.drop_index("ix_recommendations_duplicate_guard", table_name="recommendations")
    op.drop_index("ix_recommendations_today_owner", table_name="recommendations")
    with op.batch_alter_table("recommendations") as batch:
        batch.drop_constraint("uq_recommendations_tenant_generation_key", type_="unique")
        batch.drop_constraint("fk_recommendations_rule", type_="foreignkey")
        for column in ("contacted_at", "data_version", "content_checksum", "risk_flags_json", "degraded_reason", "degraded", "suggested_action", "reason", "score_breakdown_json", "generation_key", "generation_date", "policy_version", "rule_id", "owner_id"):
            batch.drop_column(column)

    with op.batch_alter_table("recommendation_rules") as batch:
        batch.drop_constraint("uq_recommendation_rules_tenant_type_version", type_="unique")
        for column in ("created_by", "published_at", "priority", "cooldown_days", "policy_version"):
            batch.drop_column(column)
