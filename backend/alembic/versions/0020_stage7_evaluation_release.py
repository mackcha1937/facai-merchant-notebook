"""0020：阶段7离线测评与发布治理加固。

revision: 0020_stage7_evaluation_release
down_revision: 0019_stage6_recommendation_feedback

复用 0008 已创建的草稿、测评、发布和审计表；只补阶段7需要的
可追溯关联、机器/人工结果字段、幂等约束和查询索引。
"""
from alembic import op
import sqlalchemy as sa


revision = "0020_stage7_evaluation_release"
down_revision = "0019_stage6_recommendation_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ai_config_drafts") as batch:
        batch.add_column(sa.Column("content_checksum", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("data_version", sa.Integer(), nullable=False, server_default="1"))

    with op.batch_alter_table("evaluation_runs") as batch:
        batch.add_column(sa.Column("draft_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("created_by", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("suite_checksum", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("runner_version", sa.String(length=50), nullable=True))
        batch.add_column(sa.Column("run_key", sa.String(length=128), nullable=True))
        batch.create_foreign_key("fk_evaluation_runs_draft", "ai_config_drafts", ["draft_id"], ["id"])
        batch.create_unique_constraint("uq_evaluation_runs_tenant_run_key", ["tenant_id", "run_key"])
    op.create_index(
        "ix_evaluation_runs_tenant_draft_created",
        "evaluation_runs",
        ["tenant_id", "draft_id", "created_at"],
    )

    with op.batch_alter_table("evaluation_case_results") as batch:
        batch.add_column(sa.Column("category", sa.String(length=60), nullable=True))
        batch.add_column(sa.Column("priority", sa.String(length=10), nullable=True))
        batch.add_column(sa.Column("safety_critical", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("expected_json", sa.Text(), nullable=True))
        batch.add_column(sa.Column("assertion_results_json", sa.Text(), nullable=True))
        batch.add_column(sa.Column("factual_score", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("safety_score", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("natural_score", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("interaction_score", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("notes", sa.Text(), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
        batch.create_unique_constraint(
            "uq_evaluation_results_tenant_run_case", ["tenant_id", "run_id", "case_id"]
        )
    op.create_index(
        "ix_evaluation_results_run_gate",
        "evaluation_case_results",
        ["tenant_id", "run_id", "safety_critical", "passed"],
    )

    for table, prefix in (
        ("prompt_releases", "prompt"),
        ("rag_releases", "rag"),
        ("recommendation_releases", "recommendation"),
    ):
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("source_draft_id", sa.Integer(), nullable=True))
            batch.add_column(sa.Column("evaluation_run_id", sa.Integer(), nullable=True))
            batch.add_column(sa.Column("published_by", sa.Integer(), nullable=True))
            batch.create_foreign_key(
                f"fk_{prefix}_releases_source_draft", "ai_config_drafts", ["source_draft_id"], ["id"]
            )
            batch.create_foreign_key(
                f"fk_{prefix}_releases_evaluation_run", "evaluation_runs", ["evaluation_run_id"], ["id"]
            )
            batch.create_unique_constraint(
                f"uq_{prefix}_releases_tenant_version", ["tenant_id", "version"]
            )
        op.create_index(
            f"ix_{prefix}_releases_tenant_status_version",
            table,
            ["tenant_id", "status", "version"],
        )

    with op.batch_alter_table("release_audits") as batch:
        batch.add_column(sa.Column("request_id", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("idempotency_key", sa.String(length=128), nullable=True))
        batch.create_unique_constraint(
            "uq_release_audits_tenant_idempotency", ["tenant_id", "idempotency_key"]
        )
    op.create_index(
        "ix_release_audits_tenant_release_created",
        "release_audits",
        ["tenant_id", "release_type", "release_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_release_audits_tenant_release_created", table_name="release_audits")
    with op.batch_alter_table("release_audits") as batch:
        batch.drop_constraint("uq_release_audits_tenant_idempotency", type_="unique")
        batch.drop_column("idempotency_key")
        batch.drop_column("request_id")

    for table, prefix in reversed((
        ("prompt_releases", "prompt"),
        ("rag_releases", "rag"),
        ("recommendation_releases", "recommendation"),
    )):
        op.drop_index(f"ix_{prefix}_releases_tenant_status_version", table_name=table)
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(f"uq_{prefix}_releases_tenant_version", type_="unique")
            batch.drop_constraint(f"fk_{prefix}_releases_evaluation_run", type_="foreignkey")
            batch.drop_constraint(f"fk_{prefix}_releases_source_draft", type_="foreignkey")
            batch.drop_column("published_by")
            batch.drop_column("evaluation_run_id")
            batch.drop_column("source_draft_id")

    op.drop_index("ix_evaluation_results_run_gate", table_name="evaluation_case_results")
    with op.batch_alter_table("evaluation_case_results") as batch:
        batch.drop_constraint("uq_evaluation_results_tenant_run_case", type_="unique")
        for column in (
            "updated_at", "notes", "interaction_score", "natural_score", "safety_score",
            "factual_score", "assertion_results_json", "expected_json", "safety_critical",
            "priority", "category",
        ):
            batch.drop_column(column)

    op.drop_index("ix_evaluation_runs_tenant_draft_created", table_name="evaluation_runs")
    with op.batch_alter_table("evaluation_runs") as batch:
        batch.drop_constraint("uq_evaluation_runs_tenant_run_key", type_="unique")
        batch.drop_constraint("fk_evaluation_runs_draft", type_="foreignkey")
        for column in ("run_key", "runner_version", "suite_checksum", "created_by", "draft_id"):
            batch.drop_column(column)

    with op.batch_alter_table("ai_config_drafts") as batch:
        batch.drop_column("data_version")
        batch.drop_column("content_checksum")
