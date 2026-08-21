"""FastAPI 应用入口。"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    agent,
    customers,
    health,
    ledger,
    model,
    packages,
    services,
    settings as settings_routes,
    trash,
    v2_stage0,
)
from app.core.config import get_settings
from app.core.database import init_db
from app.core.logging import SanitizingFilter
from app.domain.errors import DomainError, NotFoundError

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
    init_db()
    from app.agent.prompt_loader import ensure_prompt_initialized
    from app.core.database import get_session_factory

    db = get_session_factory()()
    try:
        ensure_prompt_initialized(db)
    finally:
        db.close()
    yield


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DomainError)
async def domain_error_handler(_request: Request, exc: DomainError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(NotFoundError)
async def not_found_error_handler(_request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


app.include_router(health.router)
app.include_router(model.router)
app.include_router(customers.router)
app.include_router(services.router)
app.include_router(packages.router)
app.include_router(ledger.router)
app.include_router(trash.router)
app.include_router(agent.router)
app.include_router(settings_routes.router)
app.include_router(v2_stage0.router)

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
