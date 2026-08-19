"""健康检查接口。"""
from fastapi import APIRouter

from app.core.database import check_database_connection

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health() -> dict:
    """返回后端状态与 SQLite 连接状态。"""
    db_ok, db_message = check_database_connection()
    return {
        "status": "ok",
        "database": "ok" if db_ok else "error",
        "database_message": db_message if not db_ok else "ok",
    }
