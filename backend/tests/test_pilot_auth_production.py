"""邀请内测登录、CSRF、租户隔离与生产配置回归。"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.application.auth_service import hash_invite_code, hash_password, verify_password
from app.core import database
from app.core.config import Settings, get_settings
from app.infrastructure.models import AuthSession, Base, Invite, Tenant, User, UserCredential
from app.main import app


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture()
def auth_runtime(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    original_engine, original_factory = database._engine, database._session_factory
    database._engine, database._session_factory = engine, factory
    settings = get_settings()
    monkeypatch.setattr(settings, "local_dev_owner_enabled", False)
    monkeypatch.setattr(settings, "session_secret", "test-session-secret-value-with-32-chars")
    monkeypatch.setattr(settings, "cookie_secure", False)
    monkeypatch.setattr(settings, "auto_create_schema", True)
    db = factory()
    db.add(Tenant(id=1, slug="bootstrap", display_name="启动租户", status="active"))
    db.add(User(id=1, tenant_id=1, role="owner", display_name="启动用户", status="active"))
    db.commit(); db.close()
    yield factory
    app.dependency_overrides.clear()
    database._engine, database._session_factory = original_engine, original_factory
    Base.metadata.drop_all(engine)
    engine.dispose()


def _create_invite(factory, *, tenant_id: int, slug: str, code: str, role: str = "owner"):
    db = factory()
    db.add(Tenant(id=tenant_id, slug=slug, display_name=f"{slug}店", status="active"))
    db.add(Invite(
        tenant_id=tenant_id,
        code_hash=hash_invite_code(code),
        role=role,
        expires_at=_now() + timedelta(hours=2),
    ))
    db.commit(); db.close()


def _redeem(client, code: str, login: str, display_name: str = "店主"):
    return client.post("/api/auth/redeem", json={
        "invite_code": code,
        "display_name": display_name,
        "login_name": login,
        "password": "safe-password-123",
    })


def _csrf(client) -> dict:
    return {"X-CSRF-Token": client.cookies.get("facai_csrf")}


def test_password_uses_scrypt_and_rejects_wrong_value():
    encoded = hash_password("safe-password-123")
    assert encoded.startswith("scrypt$")
    assert "safe-password-123" not in encoded
    assert verify_password("safe-password-123", encoded) is True
    assert verify_password("wrong-password", encoded) is False


def test_production_settings_fail_closed():
    with pytest.raises(RuntimeError) as exc:
        Settings(
            app_env="production",
            local_dev_owner_enabled=True,
            database_url="sqlite:////tmp/app.db",
            session_secret="short",
            auto_create_schema=True,
            cookie_secure=False,
            expose_api_docs=True,
            allowed_hosts="*",
        ).validate_production_settings()
    message = str(exc.value)
    assert "SQLite" in message and "SESSION_SECRET" in message and "LOCAL_DEV_OWNER_ENABLED" in message


def test_secure_production_settings_are_accepted():
    Settings(
        app_env="production",
        local_dev_owner_enabled=False,
        database_url="postgresql://user:pass@db.example/facai",
        session_secret="a-random-session-secret-with-32-plus-characters",
        session_cookie_name="__Host-facai_session",
        auto_create_schema=False,
        cookie_secure=True,
        expose_api_docs=False,
        allowed_hosts="pilot.example.com",
    ).validate_production_settings()


def test_managed_postgres_url_uses_psycopg_v3_driver():
    assert Settings(database_url="postgres://user:pass@db.example/facai").effective_database_url == (
        "postgresql+psycopg://user:pass@db.example/facai"
    )


def test_0021_recovers_local_create_all_auth_table_drift(tmp_path):
    database_path = tmp_path / "drift.db"
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "0020_stage7_evaluation_release")

    engine = create_engine(f"sqlite:///{database_path}")
    UserCredential.__table__.create(engine, checkfirst=True)
    AuthSession.__table__.create(engine, checkfirst=True)
    engine.dispose()

    command.upgrade(config, "head")
    connection = create_engine(f"sqlite:///{database_path}")
    with connection.connect() as conn:
        assert conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one() == "0021_pilot_auth_production"
        assert conn.exec_driver_sql("SELECT slug FROM tenants WHERE id=1").scalar_one() == "local-shop"
        indexes = {row[1] for row in conn.exec_driver_sql("PRAGMA index_list(auth_sessions)")}
        assert "ix_auth_sessions_tenant_id" in indexes
    connection.dispose()

    command.downgrade(config, "0020_stage7_evaluation_release")
    command.upgrade(config, "head")
    assert Settings(database_url="postgresql://user:pass@db.example/facai").effective_database_url == (
        "postgresql+psycopg://user:pass@db.example/facai"
    )


def test_unauthenticated_business_api_returns_401(auth_runtime):
    with TestClient(app) as client:
        response = client.get("/api/customers")
        assert response.status_code == 401
        assert response.json() == {"detail": "请先登录"}


def test_invite_redeem_is_one_time_and_sets_secure_session_boundary(auth_runtime):
    _create_invite(auth_runtime, tenant_id=2, slug="alpha", code="FC-AAAA-BBBB-CCCC")
    with TestClient(app) as client:
        response = _redeem(client, "FC-AAAA-BBBB-CCCC", "alpha_owner")
        assert response.status_code == 200
        assert response.json()["tenant_slug"] == "alpha"
        assert response.json()["role"] == "owner"
        assert client.cookies.get("facai_session")
        assert client.cookies.get("facai_csrf")
        assert "safe-password-123" not in response.text
        assert "FC-AAAA-BBBB-CCCC" not in response.text
        again = _redeem(client, "FC-AAAA-BBBB-CCCC", "another_owner")
        assert again.status_code == 400
    db = auth_runtime()
    assert db.scalar(select(UserCredential).where(UserCredential.login_name == "alpha_owner")) is not None
    assert db.query(AuthSession).count() == 1
    assert db.scalar(select(Invite).where(Invite.tenant_id == 2)).used_at is not None
    db.close()


def test_csrf_is_required_and_two_stores_are_isolated(auth_runtime):
    _create_invite(auth_runtime, tenant_id=2, slug="alpha", code="FC-AAAA-BBBB-CCCC")
    _create_invite(auth_runtime, tenant_id=3, slug="beta", code="FC-DDDD-EEEE-FFFF")
    with TestClient(app) as alpha, TestClient(app) as beta:
        assert _redeem(alpha, "FC-AAAA-BBBB-CCCC", "alpha_owner").status_code == 200
        assert _redeem(beta, "FC-DDDD-EEEE-FFFF", "beta_owner").status_code == 200
        assert alpha.post("/api/customers", json={"display_name": "Alpha顾客", "aliases": []}).status_code == 403
        created_a = alpha.post(
            "/api/customers", headers=_csrf(alpha), json={"display_name": "Alpha顾客", "aliases": []},
        )
        created_b = beta.post(
            "/api/customers", headers=_csrf(beta), json={"display_name": "Beta顾客", "aliases": []},
        )
        assert created_a.status_code == created_b.status_code == 201
        assert [row["display_name"] for row in alpha.get("/api/customers").json()] == ["Alpha顾客"]
        assert [row["display_name"] for row in beta.get("/api/customers").json()] == ["Beta顾客"]


def test_login_logout_and_wrong_password_lockout(auth_runtime, monkeypatch):
    _create_invite(auth_runtime, tenant_id=2, slug="alpha", code="FC-AAAA-BBBB-CCCC")
    monkeypatch.setattr(get_settings(), "auth_max_failed_attempts", 2)
    with TestClient(app) as bootstrap:
        assert _redeem(bootstrap, "FC-AAAA-BBBB-CCCC", "alpha_owner").status_code == 200
    with TestClient(app) as client:
        for expected in (401, 401):
            response = client.post("/api/auth/login", json={"login_name": "alpha_owner", "password": "bad"})
            assert response.status_code == expected
        locked = client.post("/api/auth/login", json={"login_name": "alpha_owner", "password": "safe-password-123"})
        assert locked.status_code == 429
    db = auth_runtime()
    credential = db.scalar(select(UserCredential).where(UserCredential.login_name == "alpha_owner"))
    credential.locked_until = _now() - timedelta(seconds=1)
    db.commit(); db.close()
    with TestClient(app) as client:
        assert client.post("/api/auth/login", json={"login_name": "alpha_owner", "password": "safe-password-123"}).status_code == 200
        assert client.get("/api/auth/me").status_code == 200
        assert client.post("/api/auth/logout", headers=_csrf(client)).status_code == 204
        assert client.get("/api/auth/me").status_code == 401
