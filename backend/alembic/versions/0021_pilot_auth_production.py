"""0021：邀请内测认证与生产会话。"""
from alembic import op
import sqlalchemy as sa

revision = "0021_pilot_auth_production"
down_revision = "0020_stage7_evaluation_release"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tenant_columns = {column["name"] for column in inspector.get_columns("tenants")}
    if "slug" not in tenant_columns:
        op.add_column("tenants", sa.Column("slug", sa.String(length=80), nullable=True))
    rows = bind.execute(sa.text("SELECT id FROM tenants ORDER BY id")).fetchall()
    for row in rows:
        slug = "local-shop" if row[0] == 1 else f"shop-{row[0]}"
        bind.execute(
            sa.text("UPDATE tenants SET slug=:slug WHERE id=:id AND (slug IS NULL OR TRIM(slug)='')"),
            {"slug": slug, "id": row[0]},
        )
    unique_names = {item.get("name") for item in sa.inspect(bind).get_unique_constraints("tenants")}
    with op.batch_alter_table("tenants") as batch:
        batch.alter_column("slug", existing_type=sa.String(length=80), nullable=False)
        if "uq_tenants_slug" not in unique_names:
            batch.create_unique_constraint("uq_tenants_slug", ["slug"])

    if "user_credentials" not in sa.inspect(bind).get_table_names():
        op.create_table(
            "user_credentials",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("login_name", sa.String(length=80), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("locked_until", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_user_credentials_tenant"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_user_credentials_user"),
            sa.UniqueConstraint("user_id", name="uq_user_credentials_user"),
            sa.UniqueConstraint("login_name", name="uq_user_credentials_login_name"),
        )
    _assert_columns(bind, "user_credentials", {
        "id", "tenant_id", "user_id", "login_name", "password_hash", "failed_attempts",
        "locked_until", "created_at", "updated_at",
    })
    _assert_constraints(
        bind, "user_credentials",
        foreign_keys={("tenant_id", "tenants"), ("user_id", "users")},
        unique_columns={"user_id", "login_name"},
    )
    _create_index_if_missing(bind, "ix_user_credentials_tenant_id", "user_credentials", ["tenant_id"])

    if "auth_sessions" not in sa.inspect(bind).get_table_names():
        op.create_table(
            "auth_sessions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("csrf_token_hash", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("last_seen_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_auth_sessions_tenant"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_auth_sessions_user"),
            sa.UniqueConstraint("token_hash", name="uq_auth_sessions_token_hash"),
        )
    _assert_columns(bind, "auth_sessions", {
        "id", "tenant_id", "user_id", "token_hash", "csrf_token_hash", "expires_at",
        "revoked_at", "last_seen_at", "created_at",
    })
    _assert_constraints(
        bind, "auth_sessions",
        foreign_keys={("tenant_id", "tenants"), ("user_id", "users")},
        unique_columns={"token_hash"},
    )
    _create_index_if_missing(bind, "ix_auth_sessions_tenant_id", "auth_sessions", ["tenant_id"])
    _create_index_if_missing(bind, "ix_auth_sessions_tenant_user", "auth_sessions", ["tenant_id", "user_id"])
    _create_index_if_missing(bind, "ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])


def _assert_columns(bind, table: str, expected: set[str]) -> None:
    actual = {column["name"] for column in sa.inspect(bind).get_columns(table)}
    missing = expected - actual
    if missing:
        raise RuntimeError(f"{table} 已存在但结构不完整，缺少列：{sorted(missing)}")


def _create_index_if_missing(bind, name: str, table: str, columns: list[str]) -> None:
    names = {item["name"] for item in sa.inspect(bind).get_indexes(table)}
    if name not in names:
        op.create_index(name, table, columns)


def _assert_constraints(bind, table: str, *, foreign_keys: set[tuple[str, str]], unique_columns: set[str]) -> None:
    inspector = sa.inspect(bind)
    actual_fks = {
        ((item.get("constrained_columns") or [None])[0], item.get("referred_table"))
        for item in inspector.get_foreign_keys(table)
    }
    actual_unique = {
        column
        for item in inspector.get_unique_constraints(table)
        for column in (item.get("column_names") or [])
    }
    if not foreign_keys.issubset(actual_fks) or not unique_columns.issubset(actual_unique):
        raise RuntimeError(f"{table} 已存在但外键或唯一约束不完整")


def downgrade() -> None:
    op.drop_index("ix_auth_sessions_expires_at", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_tenant_user", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_tenant_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_index("ix_user_credentials_tenant_id", table_name="user_credentials")
    op.drop_table("user_credentials")
    with op.batch_alter_table("tenants") as batch:
        batch.drop_constraint("uq_tenants_slug", type_="unique")
        batch.drop_column("slug")
