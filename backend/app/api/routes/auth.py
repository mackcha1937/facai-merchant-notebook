"""邀请内测登录 API。"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application import auth_service
from app.core.config import get_settings
from app.core.database import get_db
from app.infrastructure.models import Tenant, User
from app.schemas.auth import AuthUserResponse, InviteRedeemRequest, LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_session_cookies(response: Response, issued) -> None:
    settings = get_settings()
    max_age = settings.session_ttl_hours * 3600
    response.set_cookie(
        settings.session_cookie_name,
        issued.token,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )
    response.set_cookie(
        "facai_csrf",
        issued.csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )


def _payload(user: User, tenant: Tenant, mode: str = "session") -> dict:
    return AuthUserResponse(
        auth_mode=mode,
        tenant_id=tenant.id,
        tenant_slug=tenant.slug,
        tenant_name=tenant.display_name,
        user_id=user.id,
        display_name=user.display_name,
        role=user.role,
    ).model_dump()


@router.post("/redeem")
def redeem(data: InviteRedeemRequest, response: Response, db: Session = Depends(get_db)):
    try:
        issued = auth_service.redeem_invite(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _set_session_cookies(response, issued)
    return _payload(issued.user, issued.tenant)


@router.post("/login")
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    try:
        issued = auth_service.login(db, data)
    except PermissionError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    _set_session_cookies(response, issued)
    return _payload(issued.user, issued.tenant)


@router.get("/me")
def me(request: Request, db: Session = Depends(get_db)):
    user = getattr(request.state, "auth_user", None)
    tenant = getattr(request.state, "auth_tenant", None)
    if user and tenant:
        return _payload(user, tenant)
    settings = get_settings()
    if settings.local_dev_owner_enabled:
        user = db.scalar(select(User).where(User.id == settings.local_default_owner_id))
        tenant = db.scalar(select(Tenant).where(Tenant.id == settings.local_default_tenant_id))
        if user and tenant:
            return _payload(user, tenant, "local_dev")
        return AuthUserResponse(
            auth_mode="local_dev",
            tenant_id=settings.local_default_tenant_id,
            tenant_slug="local-shop",
            tenant_name="本地店铺",
            user_id=settings.local_default_owner_id,
            display_name="本地店主",
            role=settings.local_default_owner_role,
        ).model_dump()
    raise HTTPException(status_code=401, detail="请先登录")


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    settings = get_settings()
    raw_token = request.cookies.get(settings.session_cookie_name, "")
    if raw_token:
        auth_service.revoke_session(db, raw_token, settings)
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie("facai_csrf", path="/")
