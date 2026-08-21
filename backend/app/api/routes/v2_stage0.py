"""V2 阶段0：模型能力验证接口（受开发开关保护）。

- 仅在 ENABLE_STAGE0_VERIFY=true 时允许调用（会产生真实模型费用），生产默认关闭；
- 60 秒冷却，防止重复点击；
- 不返回 API Key 和敏感错误正文；
- 该接口不得进入正式生产环境。
"""
import time

from fastapi import APIRouter, HTTPException

from app.application.stage0_verify import run_all_verifications
from app.core.config import get_settings

router = APIRouter(prefix="/api/v2/stage0", tags=["v2-stage0"])

_COOLDOWN_SECONDS = 60
_last_call_ts: float = 0.0


@router.post("/verify-model")
def verify_model():
    settings = get_settings()

    # 1. 开发开关保护
    if not settings.enable_stage0_verify:
        raise HTTPException(status_code=403, detail="阶段0模型验证未开启（ENABLE_STAGE0_VERIFY=false）")

    # 2. 冷却，防重复点击
    global _last_call_ts
    now = time.time()
    if now - _last_call_ts < _COOLDOWN_SECONDS:
        raise HTTPException(status_code=429, detail=f"验证冷却中，请 {int(_COOLDOWN_SECONDS - (now - _last_call_ts))} 秒后重试")
    _last_call_ts = now

    # 3. 未配置 Key
    if not settings.is_model_configured:
        return {"configured": False, "model": settings.deepseek_model_id, "results": []}

    results = run_all_verifications(
        settings.deepseek_api_base_url.rstrip("/"),
        settings.deepseek_model_id,
        settings.deepseek_api_key,
    )
    return {
        "configured": True,
        "model": settings.deepseek_model_id,
        "base": settings.deepseek_api_base_url,
        "results": results,
    }
