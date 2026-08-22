"""模型配置状态与连通性检查接口。

- GET /api/config/model-status：owner/admin 可读（脱敏，不返回密钥）；
- POST /api/model/check：仅 admin（会产生真实模型费用）。
"""
from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.rbac import require_admin, require_owner
from app.infrastructure.llm.deepseek import DeepSeekAdapter

router = APIRouter(tags=["model"])


@router.get("/api/config/model-status")
def model_status(settings: Settings = Depends(get_settings)) -> dict:
    """返回模型是否已配置（脱敏，owner/admin 可读，不返回密钥）。"""
    require_owner()
    return {
        "configured": settings.is_model_configured,
        "model_id": settings.deepseek_model_id,
        "api_base_url": settings.deepseek_api_base_url,
    }


@router.post("/api/model/check")
def model_check(settings: Settings = Depends(get_settings)) -> dict:
    """执行一次最小连通性请求，返回脱敏结果（仅 admin）。"""
    require_admin()
    adapter = DeepSeekAdapter(settings=settings)
    result = adapter.check_connectivity()
    return {
        "configured": result.configured,
        "success": result.success,
        "model_id": result.model_id,
        "message": result.message,
    }
