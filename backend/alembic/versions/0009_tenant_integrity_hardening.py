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

# 0009 upgrade 第 3 步新增的 V2 主要关系外键（downgrade 必须显式撤销）。
# 注意：customer_aliases/packages/ledger_entries 的关系外键会在 V1 七表重建时随表一并移除，
# 因此不在此列。
RELATION_FKS = [
    ("users", "fk_users_tenant"),
    ("invites", "fk_invites_tenant"),
    ("customer_facts", "fk_customer_facts_customer"),
    ("recommendations", "fk_recommendations_customer"),
    ("conversation_sessions", "fk_sessions_thread"),
    ("messages", "fk_messages_session"),
    ("message_blocks", "fk_blocks_message"),
    ("entity_mentions", "fk_mentions_message"),
    ("context_summaries", "fk_summaries_session"),
    ("knowledge_documents", "fk_kd_tenant"),
    ("embedding_records", "fk_er_tenant"),
    ("embedding_records", "fk_er_document"),
    ("evaluation_case_results", "fk_ecr_run"),
]


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
    bind = op.get_bind()
    bind.exec_driver_sql("PRAGMA foreign_keys=OFF")

    # 移除 tenant 索引（先删，避免重建表时索引引用 tenant_id 失败）
    for table in V1_TABLES:
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
    for table in SUBTABLE_BACKFILL.keys():
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
    op.drop_index("ix_packages_tenant_customer", table_name="packages")
    op.drop_index("ix_ledger_tenant_customer", table_name="ledger_entries")
    op.drop_index("ix_customer_aliases_tenant_customer", table_name="customer_aliases")

    # 撤销 0009 新增的 V2 主要关系外键（13 个）
    for table, constraint in RELATION_FKS:
        with op.batch_alter_table(table, recreate="always") as batch:
            batch.drop_constraint(constraint, type_="foreignkey")

    # 移除 6 张子表 tenant_id 列
    for table in SUBTABLE_BACKFILL.keys():
        with op.batch_alter_table(table, recreate="always") as batch:
            batch.drop_column("tenant_id")

    # V1 七表恢复到 0008 状态：tenant_id 可空、无 tenant 外键（手动重建）
    _rebuild_v1_table_nullable_tenant(bind, "customers", [
        "id INTEGER NOT NULL PRIMARY KEY",
        "display_name VARCHAR(100) NOT NULL",
        "created_at DATETIME",
        "updated_at DATETIME",
        "deleted_at DATETIME",
        "tenant_id INTEGER",
    ], ["id", "display_name", "created_at", "updated_at", "deleted_at", "tenant_id"])
    _rebuild_v1_table_nullable_tenant(bind, "customer_aliases", [
        "id INTEGER NOT NULL PRIMARY KEY",
        "customer_id INTEGER NOT NULL",
        "alias VARCHAR(100) NOT NULL",
        "deleted_at DATETIME",
        "tenant_id INTEGER",
    ], ["id", "customer_id", "alias", "deleted_at", "tenant_id"])
    _rebuild_v1_table_nullable_tenant(bind, "services", [
        "id INTEGER NOT NULL PRIMARY KEY",
        "name VARCHAR(100) NOT NULL",
        "status VARCHAR(20) NOT NULL",
        "deleted_at DATETIME",
        "tenant_id INTEGER",
    ], ["id", "name", "status", "deleted_at", "tenant_id"])
    _rebuild_v1_table_nullable_tenant(bind, "packages", [
        "id INTEGER NOT NULL PRIMARY KEY",
        "customer_id INTEGER NOT NULL",
        "service_id INTEGER NOT NULL",
        "total_count INTEGER NOT NULL",
        "opening_used_count INTEGER NOT NULL",
        "price_cents INTEGER",
        "purchased_on VARCHAR(20)",
        "status VARCHAR(20) NOT NULL",
        "deleted_at DATETIME",
        "tenant_id INTEGER",
    ], ["id", "customer_id", "service_id", "total_count", "opening_used_count", "price_cents", "purchased_on", "status", "deleted_at", "tenant_id"])
    _rebuild_v1_table_nullable_tenant(bind, "ledger_entries", [
        "id INTEGER NOT NULL PRIMARY KEY",
        "customer_id INTEGER NOT NULL",
        "entry_type VARCHAR(30) NOT NULL",
        "package_id INTEGER",
        "service_id INTEGER",
        "product_name VARCHAR(100)",
        "quantity INTEGER NOT NULL",
        "price_cents INTEGER",
        "occurred_on VARCHAR(20)",
        "original_input TEXT",
        "agent_prompt_version INTEGER",
        "deleted_at DATETIME",
        "tenant_id INTEGER",
    ], ["id", "customer_id", "entry_type", "package_id", "service_id", "product_name", "quantity", "price_cents", "occurred_on", "original_input", "agent_prompt_version", "deleted_at", "tenant_id"])
    _rebuild_v1_table_nullable_tenant(bind, "prompt_versions", [
        "id INTEGER NOT NULL PRIMARY KEY",
        "version INTEGER NOT NULL",
        "content TEXT NOT NULL",
        "created_at DATETIME",
        "is_active BOOLEAN NOT NULL",
        "tenant_id INTEGER",
    ], ["id", "version", "content", "created_at", "is_active", "tenant_id"])
    _rebuild_v1_table_nullable_tenant(bind, "agent_proposals", [
        "id INTEGER NOT NULL PRIMARY KEY",
        "original_input TEXT NOT NULL",
        "parsed_json TEXT NOT NULL",
        "prompt_version INTEGER",
        "status VARCHAR(20) NOT NULL",
        "created_at DATETIME",
        "confirmed_at DATETIME",
        "tenant_id INTEGER",
    ], ["id", "original_input", "parsed_json", "prompt_version", "status", "created_at", "confirmed_at", "tenant_id"])


def _rebuild_v1_table_nullable_tenant(bind, table, column_defs, columns):
    cols = ", ".join(column_defs)
    col_list = ", ".join(columns)
    bind.exec_driver_sql(f"CREATE TABLE _tmp_{table} ({cols})")
    bind.exec_driver_sql(f"INSERT INTO _tmp_{table} ({col_list}) SELECT {col_list} FROM {table}")
    bind.exec_driver_sql(f"DROP TABLE {table}")
    bind.exec_driver_sql(f"ALTER TABLE _tmp_{table} RENAME TO {table}")
