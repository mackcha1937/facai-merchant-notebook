"""邀请码开通、密码登录与不透明会话。"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.infrastructure.models import AuthSession, Invite, Tenant, User, UserCredential
from app.schemas.auth import InviteRedeemRequest, LoginRequest


def _utc_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalize_login_name(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized.replace("-", "").replace("_", "").isalnum():
        raise ValueError("登录名只能包含字母、数字、下划线和短横线")
    return normalized


def _hmac_digest(value: str, purpose: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    secret = settings.auth_secret
    if len(secret) < 16:
        raise RuntimeError("认证 Secret 未配置")
    return hmac.new(secret.encode(), f"{purpose}:{value}".encode(), hashlib.sha256).hexdigest()


def hash_invite_code(code: str, settings: Settings | None = None) -> str:
    return _hmac_digest(code.strip().upper(), "invite", settings)


def hash_session_token(token: str, settings: Settings | None = None) -> str:
    return _hmac_digest(token, "session", settings)


def hash_password(password: str) -> str:
    if len(password) < 10:
        raise ValueError("密码至少 10 位")
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt$16384$8$1${salt.hex()}${derived.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_hex, digest_hex = encoded.split("$")
        if algorithm != "scrypt":
            return False
        derived = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt_hex), n=int(n), r=int(r), p=int(p), dklen=32,
        )
        return hmac.compare_digest(derived.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


_DUMMY_PASSWORD_HASH = hash_password("facai-dummy-password-never-used")


@dataclass(frozen=True)
class IssuedSession:
    token: str
    csrf_token: str
    row: AuthSession
    user: User
    tenant: Tenant


def _issue_session(db: Session, user: User, tenant: Tenant, settings: Settings) -> IssuedSession:
    token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(24)
    now = _utc_naive()
    row = AuthSession(
        tenant_id=tenant.id,
        user_id=user.id,
        token_hash=hash_session_token(token, settings),
        csrf_token_hash=hash_session_token(csrf_token, settings),
        expires_at=now + timedelta(hours=settings.session_ttl_hours),
        last_seen_at=now,
    )
    db.add(row)
    user.last_login_at = now
    db.commit()
    db.refresh(row)
    return IssuedSession(token=token, csrf_token=csrf_token, row=row, user=user, tenant=tenant)


def _initialize_tenant_prompt(db: Session, tenant_id: int, user_id: int, role: str) -> None:
    """首次开通时为该租户创建提示词初始版，不在应用启动时写全局默认租户。"""
    from app.agent.prompt_loader import load_template
    from app.core.tenant import (
        reset_current_owner_id,
        reset_current_role,
        reset_current_tenant_id,
        set_current_owner_id,
        set_current_role,
        set_current_tenant_id,
    )
    from app.repositories import prompts as prompt_repo

    tenant_token = set_current_tenant_id(tenant_id)
    role_token = set_current_role(role)
    owner_token = set_current_owner_id(user_id)
    try:
        if prompt_repo.count_versions(db) == 0:
            prompt_repo.create_version(db, 1, load_template(), active=True)
    finally:
        reset_current_owner_id(owner_token)
        reset_current_role(role_token)
        reset_current_tenant_id(tenant_token)


def redeem_invite(db: Session, data: InviteRedeemRequest, settings: Settings | None = None) -> IssuedSession:
    settings = settings or get_settings()
    now = _utc_naive()
    code_hash = hash_invite_code(data.invite_code, settings)
    # PostgreSQL 上锁定邀请码行，防止两个并发兑换同时通过一次性检查。
    invite = db.scalar(select(Invite).where(Invite.code_hash == code_hash).with_for_update())
    if invite is None or invite.used_at is not None or (invite.expires_at and invite.expires_at <= now):
        verify_password(data.password, _DUMMY_PASSWORD_HASH)
        raise ValueError("邀请码无效或已过期")
    tenant = db.scalar(select(Tenant).where(Tenant.id == invite.tenant_id, Tenant.status == "active"))
    if tenant is None:
        raise ValueError("邀请码无效或已过期")
    login_name = normalize_login_name(data.login_name)
    if db.scalar(select(UserCredential.id).where(UserCredential.login_name == login_name)) is not None:
        raise ValueError("该登录名已被使用")
    role = invite.role if invite.role in {"owner", "admin"} else "owner"
    user = User(tenant_id=tenant.id, role=role, display_name=data.display_name.strip(), status="active")
    db.add(user)
    db.flush()
    db.add(UserCredential(
        tenant_id=tenant.id,
        user_id=user.id,
        login_name=login_name,
        password_hash=hash_password(data.password),
    ))
    invite.used_at = now
    db.flush()
    _initialize_tenant_prompt(db, tenant.id, user.id, role)
    return _issue_session(db, user, tenant, settings)


def login(db: Session, data: LoginRequest, settings: Settings | None = None) -> IssuedSession:
    settings = settings or get_settings()
    now = _utc_naive()
    login_name = normalize_login_name(data.login_name)
    credential = db.scalar(select(UserCredential).where(UserCredential.login_name == login_name))
    if credential is None:
        verify_password(data.password, _DUMMY_PASSWORD_HASH)
        raise ValueError("登录名或密码错误")
    if credential.locked_until and credential.locked_until > now:
        raise PermissionError("登录失败次数过多，请稍后再试")
    if not verify_password(data.password, credential.password_hash):
        credential.failed_attempts += 1
        if credential.failed_attempts >= settings.auth_max_failed_attempts:
            credential.locked_until = now + timedelta(minutes=settings.auth_lockout_minutes)
            credential.failed_attempts = 0
        db.commit()
        raise ValueError("登录名或密码错误")
    user = db.scalar(select(User).where(User.id == credential.user_id, User.status == "active"))
    tenant = db.scalar(select(Tenant).where(Tenant.id == credential.tenant_id, Tenant.status == "active"))
    if user is None or tenant is None or user.tenant_id != tenant.id:
        raise ValueError("账号已停用")
    credential.failed_attempts = 0
    credential.locked_until = None
    db.flush()
    return _issue_session(db, user, tenant, settings)


def revoke_session(db: Session, token: str, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    row = db.scalar(select(AuthSession).where(AuthSession.token_hash == hash_session_token(token, settings)))
    if row and row.revoked_at is None:
        row.revoked_at = _utc_naive()
        db.commit()
