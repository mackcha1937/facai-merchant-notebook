"""从 HttpOnly 会话 Cookie 建立 tenant / user 权威上下文。"""
from datetime import datetime, timezone

from fastapi.responses import JSONResponse
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware

from app.application.auth_service import hash_session_token
from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.tenant import (
    reset_current_owner_id,
    reset_current_role,
    reset_current_tenant_id,
    set_current_owner_id,
    set_current_role,
    set_current_tenant_id,
)
from app.infrastructure.models import AuthSession, Tenant, User

PUBLIC_API_PATHS = {
    "/api/health",
    "/api/auth/login",
    "/api/auth/redeem",
}
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _utc_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PilotAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        settings = get_settings()
        tenant_token = role_token = user_token = None
        db = None
        try:
            if request.url.path.startswith("/api/") and request.url.path not in PUBLIC_API_PATHS:
                raw_token = request.cookies.get(settings.session_cookie_name, "")
                if raw_token:
                    db = get_session_factory()()
                    now = _utc_naive()
                    session = db.scalar(select(AuthSession).where(
                        AuthSession.token_hash == hash_session_token(raw_token, settings),
                        AuthSession.revoked_at.is_(None),
                        AuthSession.expires_at > now,
                    ))
                    user = db.scalar(select(User).where(User.id == session.user_id, User.status == "active")) if session else None
                    tenant = db.scalar(select(Tenant).where(Tenant.id == session.tenant_id, Tenant.status == "active")) if session else None
                    if session and user and tenant and user.tenant_id == tenant.id:
                        if request.method.upper() not in SAFE_METHODS:
                            csrf_header = request.headers.get("X-CSRF-Token", "")
                            csrf_cookie = request.cookies.get("facai_csrf", "")
                            if not csrf_header or csrf_header != csrf_cookie or not secrets_equal(
                                session.csrf_token_hash, hash_session_token(csrf_header, settings),
                            ):
                                return JSONResponse(status_code=403, content={"detail": "CSRF 校验失败"})
                        tenant_token = set_current_tenant_id(tenant.id)
                        role_token = set_current_role(user.role)
                        user_token = set_current_owner_id(user.id)
                        request.state.auth_session = session
                        request.state.auth_user = user
                        request.state.auth_tenant = tenant
                        session.last_seen_at = now
                        db.commit()
                    elif not settings.local_dev_owner_enabled:
                        return JSONResponse(status_code=401, content={"detail": "请先登录"})
                elif not settings.local_dev_owner_enabled:
                    return JSONResponse(status_code=401, content={"detail": "请先登录"})
            return await call_next(request)
        finally:
            if user_token is not None:
                reset_current_owner_id(user_token)
            if role_token is not None:
                reset_current_role(role_token)
            if tenant_token is not None:
                reset_current_tenant_id(tenant_token)
            if db is not None:
                db.close()


def secrets_equal(left: str, right: str) -> bool:
    import hmac
    return hmac.compare_digest(left, right)
