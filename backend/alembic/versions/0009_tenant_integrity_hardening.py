"""0009：租户完整性加固。

revision: 0009_tenant_integrity_hardening
down_revision: 0008_release

内容：
1. V1 七张表 tenant_id 改 NOT NULL + 外键 tenants.id + 索引；
2. 补齐 6 张业务子表 tenant_id 并通过父级回填；
3. 补 V2 主要关系外键。

不删除、重命名、覆盖任何 V1 权威字段。
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_tenant_integrity_hardening"
down_revision = "0008_release"
branch_labels = None
depends_on = None

# V1 七表：加 tenant NOT NULL + 外键 + 索引
V1_TABLES = ["customers", "customer_aliases", "services", "packages", "ledger_entries", "prompt_versions", "agent_proposals"]

# 业务子表：加 tenant_id，通过父级回填
SUBTABLE_BACKFILL = {
    "conversation_sessions": ("thread_id", "conversation_threads"),
    "messages": ("session_id", "conversation_sessions"),
    "message_blocks": ("message_id", "messages"),
    "entity_mentions": ("message_id", "messages"),
    "context_summaries": ("session_id", "conversation_sessions"),
    "evaluation_case_results": ("run_id", "evaluation_runs"),
}


def upgrade() -> None:
    # 1. V1 七表 tenant_id NOT NULL + 外键 + 索引
    for table in V1_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.alter_column("tenant_id", existing_type=sa.Integer(), nullable=False)
            batch.create_foreign_key(f"fk_{table}_tenant", "tenants", ["tenant_id"], ["id"])
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])

    # 高频复合索引
    op.create_index("ix_packages_tenant_customer", "packages", ["tenant_id", "customer_id"])
    op.create_index("ix_ledger_tenant_customer", "ledger_entries", ["tenant_id", "customer_id"])
    op.create_index("ix_customer_aliases_tenant_customer", "customer_aliases", ["tenant_id", "customer_id"])

    # 2. 补齐子表 tenant_id（先加列，回填，再 NOT NULL + 外键 + 索引）
    for table, (fk_col, parent) in SUBTABLE_BACKFILL.items():
        op.add_column(table, sa.Column("tenant_id", sa.Integer(), nullable=True))
        # 通过父级关系回填 tenant_id
        op.execute(
            sa.text(
                f"UPDATE {table} SET tenant_id = "
                f"(SELECT p.tenant_id FROM {parent} p WHERE p.id = {table}.{fk_col})"
            )
        )
        with op.batch_alter_table(table) as batch:
            batch.alter_column("tenant_id", existing_type=sa.Integer(), nullable=False)
            batch.create_foreign_key(f"fk_{table}_tenant", "tenants", ["tenant_id"], ["id"])
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])

    # 3. V2 主要关系外键
    # users / invites -> tenants
    with op.batch_alter_table("users") as batch:
        batch.create_foreign_key("fk_users_tenant", "tenants", ["tenant_id"], ["id"])
    with op.batch_alter_table("invites") as batch:
        batch.create_foreign_key("fk_invites_tenant", "tenants", ["tenant_id"], ["id"])

    # customer_alias / package / ledger / customer_fact / recommendation -> customer
    with op.batch_alter_table("customer_aliases") as batch:
        batch.create_foreign_key("fk_customer_aliases_customer", "customers", ["customer_id"], ["id"])
    with op.batch_alter_table("packages") as batch:
        batch.create_foreign_key("fk_packages_customer", "customers", ["customer_id"], ["id"])
        batch.create_foreign_key("fk_packages_service", "services", ["service_id"], ["id"])
    with op.batch_alter_table("ledger_entries") as batch:
        batch.create_foreign_key("fk_ledger_customer", "customers", ["customer_id"], ["id"])
    with op.batch_alter_table("customer_facts") as batch:
        batch.create_foreign_key("fk_customer_facts_customer", "customers", ["customer_id"], ["id"])
    with op.batch_alter_table("recommendations") as batch:
        batch.create_foreign_key("fk_recommendations_customer", "customers", ["customer_id"], ["id"])

    # conversation 子表 -> 父
    with op.batch_alter_table("conversation_sessions") as batch:
        batch.create_foreign_key("fk_sessions_thread", "conversation_threads", ["thread_id"], ["id"])
    with op.batch_alter_table("messages") as batch:
        batch.create_foreign_key("fk_messages_session", "conversation_sessions", ["session_id"], ["id"])
    with op.batch_alter_table("message_blocks") as batch:
        batch.create_foreign_key("fk_blocks_message", "messages", ["message_id"], ["id"])
    with op.batch_alter_table("entity_mentions") as batch:
        batch.create_foreign_key("fk_mentions_message", "messages", ["message_id"], ["id"])
    with op.batch_alter_table("context_summaries") as batch:
        batch.create_foreign_key("fk_summaries_session", "conversation_sessions", ["session_id"], ["id"])

    # knowledge / embedding -> 父
    with op.batch_alter_table("knowledge_documents") as batch:
        batch.create_foreign_key("fk_kd_tenant", "tenants", ["tenant_id"], ["id"])
    with op.batch_alter_table("embedding_records") as batch:
        batch.create_foreign_key("fk_er_tenant", "tenants", ["tenant_id"], ["id"])
        batch.create_foreign_key("fk_er_document", "knowledge_documents", ["document_id"], ["id"])

    # evaluation_case_result -> evaluation_run
    with op.batch_alter_table("evaluation_case_results") as batch:
        batch.create_foreign_key("fk_ecr_run", "evaluation_runs", ["run_id"], ["id"])


def downgrade() -> None:
    # 回滚时临时关闭外键，避免 batch 重建表时外键干扰
    bind = op.get_bind()
    bind.exec_driver_sql("PRAGMA foreign_keys=OFF")

    # 先移除 tenant 索引（避免重建表时索引引用 tenant_id 失败）
    for table in V1_TABLES:
        try:
            op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        except Exception:  # noqa: BLE001
            pass
    for table in SUBTABLE_BACKFILL.keys():
        try:
            op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        except Exception:  # noqa: BLE001
            pass
    for name, tbl in [
        ("ix_packages_tenant_customer", "packages"),
        ("ix_ledger_tenant_customer", "ledger_entries"),
        ("ix_customer_aliases_tenant_customer", "customer_aliases"),
    ]:
        try:
            op.drop_index(name, table_name=tbl)
        except Exception:  # noqa: BLE001
            pass

    # 移除 6 张子表的 tenant_id 列（batch 重建）
    for table in SUBTABLE_BACKFILL.keys():
        with op.batch_alter_table(table) as batch:
            batch.drop_column("tenant_id")

    # V1 七表的 tenant_id 的 NOT NULL/外键不在此撤销；
    # 继续 downgrade 到 0003 时会通过 drop tenant_id 列一并移除，不删除 V1 权威字段。
