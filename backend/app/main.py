"""FastAPI 应用入口。"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import customers, health, ledger, model, packages, services, trash
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
