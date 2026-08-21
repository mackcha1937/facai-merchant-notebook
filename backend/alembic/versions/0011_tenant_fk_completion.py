"""0011：补齐所有 tenant 外键 + 索引 + 清理重复父级外键。

revision: 0011_tenant_fk_completion
down_revision: 0010_product_name_migration
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_tenant_fk_completion"
down_revision = "0010_product_name_migration"
branch_labels = None
depends_on = None

# 缺 tenant 外键的 18 张表（自动扫描结果）
MISSING_TENANT_FK = [
    "ai_config_drafts",
    "conversation_threads",
    "customer_facts",
    "evaluation_runs",
    "follow_up_feedback",
    "message_drafts",
    "owner_ai_feedback",
    "pending_actions",
    "product_aliases",
    "product_knowledge_versions",
    "products",
    "prompt_releases",
    "rag_releases",
    "recommendation_releases",
    "recommendation_rules",
    "recommendations",
    "release_audits",
    "service_knowledge_versions",
    "voice_turns",
]


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("PRAGMA foreign_keys=OFF")

    # 1. 18 张表补 tenant 外键 + 索引
    for table in MISSING_TENANT_FK:
        with op.batch_alter_table(table) as batch:
            batch.create_foreign_key(f"fk_{table}_tenant", "tenants", ["tenant_id"], ["id"])
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])

    # 2. 清理重复父级外键（手动重建 3 张表，只保留正确外键）
    _rebuild_packages(bind)
    _rebuild_ledger(bind)
    _rebuild_customer_aliases(bind)


def _rebuild_packages(bind):
    bind.exec_driver_sql(
        """
        CREATE TABLE _packages_new (
            id INTEGER NOT NULL PRIMARY KEY,
            tenant_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL,
            service_id INTEGER NOT NULL,
            total_count INTEGER NOT NULL,
            opening_used_count INTEGER NOT NULL,
            price_cents INTEGER,
            purchased_on VARCHAR(20),
            status VARCHAR(20) NOT NULL,
            deleted_at DATETIME,
            CONSTRAINT fk_packages_tenant FOREIGN KEY(tenant_id) REFERENCES tenants(id),
            CONSTRAINT fk_packages_customer FOREIGN KEY(customer_id) REFERENCES customers(id),
            CONSTRAINT fk_packages_service FOREIGN KEY(service_id) REFERENCES services(id)
        )
        """
    )
    bind.exec_driver_sql(
        "INSERT INTO _packages_new (id, tenant_id, customer_id, service_id, total_count, opening_used_count, price_cents, purchased_on, status, deleted_at) "
        "SELECT id, tenant_id, customer_id, service_id, total_count, opening_used_count, price_cents, purchased_on, status, deleted_at FROM packages"
    )
    bind.exec_driver_sql("DROP TABLE packages")
    bind.exec_driver_sql("ALTER TABLE _packages_new RENAME TO packages")
    op.create_index("ix_packages_tenant_id", "packages", ["tenant_id"])
    op.create_index("ix_packages_tenant_customer", "packages", ["tenant_id", "customer_id"])


def _rebuild_ledger(bind):
    bind.exec_driver_sql(
        """
        CREATE TABLE _ledger_new (
            id INTEGER NOT NULL PRIMARY KEY,
            tenant_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL,
            entry_type VARCHAR(30) NOT NULL,
            package_id INTEGER,
            service_id INTEGER,
            product_id INTEGER,
            product_name VARCHAR(100),
            quantity INTEGER NOT NULL,
            price_cents INTEGER,
            occurred_on VARCHAR(20),
            original_input TEXT,
            agent_prompt_version INTEGER,
            deleted_at DATETIME,
            CONSTRAINT fk_ledger_tenant FOREIGN KEY(tenant_id) REFERENCES tenants(id),
            CONSTRAINT fk_ledger_customer FOREIGN KEY(customer_id) REFERENCES customers(id),
            CONSTRAINT fk_ledger_package FOREIGN KEY(package_id) REFERENCES packages(id),
            CONSTRAINT fk_ledger_service FOREIGN KEY(service_id) REFERENCES services(id)
        )
        """
    )
    bind.exec_driver_sql(
        "INSERT INTO _ledger_new (id, tenant_id, customer_id, entry_type, package_id, service_id, product_id, product_name, quantity, price_cents, occurred_on, original_input, agent_prompt_version, deleted_at) "
        "SELECT id, tenant_id, customer_id, entry_type, package_id, service_id, product_id, product_name, quantity, price_cents, occurred_on, original_input, agent_prompt_version, deleted_at FROM ledger_entries"
    )
    bind.exec_driver_sql("DROP TABLE ledger_entries")
    bind.exec_driver_sql("ALTER TABLE _ledger_new RENAME TO ledger_entries")
    op.create_index("ix_ledger_entries_tenant_id", "ledger_entries", ["tenant_id"])
    op.create_index("ix_ledger_tenant_customer", "ledger_entries", ["tenant_id", "customer_id"])


def _rebuild_customer_aliases(bind):
    bind.exec_driver_sql(
        """
        CREATE TABLE _aliases_new (
            id INTEGER NOT NULL PRIMARY KEY,
            tenant_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL,
            alias VARCHAR(100) NOT NULL,
            deleted_at DATETIME,
            CONSTRAINT fk_aliases_tenant FOREIGN KEY(tenant_id) REFERENCES tenants(id),
            CONSTRAINT fk_aliases_customer FOREIGN KEY(customer_id) REFERENCES customers(id)
        )
        """
    )
    bind.exec_driver_sql(
        "INSERT INTO _aliases_new (id, tenant_id, customer_id, alias, deleted_at) "
        "SELECT id, tenant_id, customer_id, alias, deleted_at FROM customer_aliases"
    )
    bind.exec_driver_sql("DROP TABLE customer_aliases")
    bind.exec_driver_sql("ALTER TABLE _aliases_new RENAME TO customer_aliases")
    op.create_index("ix_customer_aliases_tenant_id", "customer_aliases", ["tenant_id"])
    op.create_index("ix_customer_aliases_tenant_customer", "customer_aliases", ["tenant_id", "customer_id"])


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("PRAGMA foreign_keys=OFF")
    # 移除 18 表 tenant 索引（外键随表结构保留，不删除数据）
    for table in MISSING_TENANT_FK:
        try:
            op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        except Exception:
            raise
