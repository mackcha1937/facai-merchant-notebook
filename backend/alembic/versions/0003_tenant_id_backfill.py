"""0003：现有业务表加 tenant_id 并回填默认租户。

revision: 0003_tenant_id_backfill
down_revision: 0002_tenant_user_invite

- 创建默认租户（display_name=默认店铺）和默认 owner；
- 给 7 张业务表加 tenant_id 列；
- 回填 tenant_id 为默认租户。
downgrade 仅移除 tenant_id 列，不删除任何 V1 账本数据。
"""
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "0003_tenant_id_backfill"
down_revision = "0002_tenant_user_invite"
branch_labels = None
depends_on = None

BUSINESS_TABLES = [
    "customers",
    "customer_aliases",
    "services",
    "packages",
    "ledger_entries",
    "prompt_versions",
    "agent_proposals",
]


def _now() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(" ")


def upgrade() -> None:
    now = _now()

    # 1. 创建默认租户
    op.execute(
        sa.text(
            "INSERT INTO tenants (id, display_name, status, created_at, updated_at) "
            "VALUES (1, '默认店铺', 'active', :now, :now)"
        ).bindparams(now=now)
    )
    # 2. 创建默认 owner
    op.execute(
        sa.text(
            "INSERT INTO users (id, tenant_id, role, display_name, status, created_at, updated_at) "
            "VALUES (1, 1, 'owner', '默认店主', 'active', :now, :now)"
        ).bindparams(now=now)
    )

    # 3. 给业务表加 tenant_id 列（SQLite 先加可空列）
    for table in BUSINESS_TABLES:
        op.add_column(table, sa.Column("tenant_id", sa.Integer(), nullable=True))

    # 4. 回填默认租户
    for table in BUSINESS_TABLES:
        op.execute(sa.text(f"UPDATE {table} SET tenant_id = 1 WHERE tenant_id IS NULL"))


def downgrade() -> None:
    # 仅移除 tenant_id 列，不删除账本数据
    with op.batch_alter_table("customers") as b:
        b.drop_column("tenant_id")
    with op.batch_alter_table("customer_aliases") as b:
        b.drop_column("tenant_id")
    with op.batch_alter_table("services") as b:
        b.drop_column("tenant_id")
    with op.batch_alter_table("packages") as b:
        b.drop_column("tenant_id")
    with op.batch_alter_table("ledger_entries") as b:
        b.drop_column("tenant_id")
    with op.batch_alter_table("prompt_versions") as b:
        b.drop_column("tenant_id")
    with op.batch_alter_table("agent_proposals") as b:
        b.drop_column("tenant_id")
    # 保留默认租户/用户（不删除），仅作为残留记录
