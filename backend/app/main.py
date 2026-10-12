"""FastAPI 应用入口。"""
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import (
    agent,
    auth,
    customers,
    health,
    ledger,
    model,
    packages,
    services,
    settings as settings_routes,
    trash,
    v2_stage0,
    v2_stage1,
    v2_stage2,
    v2_stage3,
    v2_stage4,
    v2_stage5,
    v2_stage6,
    v2_stage7,
    v2_stage8,
)
from app.core.config import get_settings
from app.core.auth_middleware import PilotAuthMiddleware
from app.core.database import init_db
from app.core.logging import SanitizingFilter
from app.domain.errors import ConflictError, DomainError, NotFoundError, PermissionDeniedError

settings = get_settings()


def _apply_log_filter() -> None:
    """为根日志和 uvicorn 日志挂上脱敏过滤器。"""
    sanitizing_filter = SanitizingFilter(lambda: (get_settings().deepseek_api_key or None))
    root = logging.getLogger()
    root.addFilter(sanitizing_filter)
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logging.getLogger(name).addFilter(sanitizing_filter)


_apply_log_filter()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    runtime_settings = get_settings()
    runtime_settings.validate_production_settings()
    init_db()
    from app.agent.prompt_loader import ensure_prompt_initialized
    from app.core.database import get_session_factory

    if runtime_settings.local_dev_owner_enabled:
        db = get_session_factory()()
        try:
            ensure_prompt_initialized(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs" if settings.expose_api_docs else None,
    redoc_url="/redoc" if settings.expose_api_docs else None,
    openapi_url="/openapi.json" if settings.expose_api_docs else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_host_list)
app.add_middleware(PilotAuthMiddleware)


@app.middleware("http")
async def security_response_headers(request: Request, call_next):
    """本地与远程共用的最小响应安全基线；HTTPS时才发送HSTS。"""
    incoming_id = request.headers.get("X-Request-ID", "")
    try:
        trace_id = str(uuid.UUID(incoming_id)) if incoming_id else str(uuid.uuid4())
    except ValueError:
        trace_id = str(uuid.uuid4())
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = trace_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), geolocation=(), microphone=(self)"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    elif request.url.path not in {"/docs", "/redoc", "/openapi.json"}:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; base-uri 'self'; frame-ancestors 'none'; "
            "object-src 'none'; form-action 'self'; img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'"
        )
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(DomainError)
async def domain_error_handler(_request: Request, exc: DomainError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(PermissionDeniedError)
async def permission_denied_handler(_request: Request, exc: PermissionDeniedError):
    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.exception_handler(NotFoundError)
async def not_found_error_handler(_request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
async def conflict_error_handler(_request: Request, exc: ConflictError):
    return JSONResponse(
        status_code=409,
        content={"detail": str(exc), "recoverable": True, **exc.payload},
    )


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(model.router)
app.include_router(customers.router)
app.include_router(services.router)
app.include_router(packages.router)
app.include_router(ledger.router)
app.include_router(trash.router)
app.include_router(agent.router)
app.include_router(settings_routes.router)
app.include_router(v2_stage0.router)
app.include_router(v2_stage1.router)
app.include_router(v2_stage2.router)
app.include_router(v2_stage3.router)
app.include_router(v2_stage4.router)
app.include_router(v2_stage5.router)
app.include_router(v2_stage6.router)
app.include_router(v2_stage7.router)
app.include_router(v2_stage8.router)

# ---- 前后端合并：后端托管前端构建产物（单端口运行） ----
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    """SPA 回退：非 API 路径返回前端页面。"""
    if FRONTEND_DIST.exists():
        candidate = (FRONTEND_DIST / full_path).resolve()
        if candidate.is_file() and FRONTEND_DIST.resolve() in candidate.parents:
            return FileResponse(candidate)
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(index)
    return JSONResponse(
        status_code=404,
        content={"detail": "前端未构建，请先在 frontend 目录运行 npm run build"},
    )
