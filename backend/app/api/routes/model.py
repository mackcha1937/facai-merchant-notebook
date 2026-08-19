"""模型配置状态与连通性检查接口。

只返回“是否配置”和连通状态，绝不返回 API Key 内容。
"""
from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.infrastructure.llm.deepseek import DeepSeekAdapter

router = APIRouter(tags=["model"])


@router.get("/api/config/model-status")
def model_status(settings: Settings = Depends(get_settings)) -> dict:
    """返回模型是否已配置（不返回密钥）。"""
    return {
        "configured": settings.is_model_configured,
        "model_id": settings.deepseek_model_id,
        "api_base_url": settings.deepseek_api_base_url,
    }


@router.post("/api/model/check")
def model_check(settings: Settings = Depends(get_settings)) -> dict:
    """执行一次最小连通性请求，返回脱敏结果。"""
    adapter = DeepSeekAdapter(settings=settings)
    result = adapter.check_connectivity()
    return {
        "configured": result.configured,
        "success": result.success,
        "model_id": result.model_id,
        "message": result.message,
    }
