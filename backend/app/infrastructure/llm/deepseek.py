"""DeepSeek 模型适配器（OpenAI 兼容接口）。

阶段0只实现最小连通性检查：
- 使用配置的 base URL + model ID + API Key 发起一次 chat/completions 请求
- 绝不修改 model ID，绝不猜测或替换
- 所有错误信息经过脱敏，不包含 API Key
"""
import httpx

from app.core.logging import sanitize_text
from app.infrastructure.llm.base import ModelAdapter, ModelCheckResult


class DeepSeekAdapter(ModelAdapter):
    def __init__(self, settings=None):
        if settings is None:
            from app.core.config import get_settings

            settings = get_settings()
        self.settings = settings

    def check_connectivity(self) -> ModelCheckResult:
        s = self.settings
        secret = getattr(s, "deepseek_api_key", "") or ""

        if not s.is_model_configured:
            return ModelCheckResult(
                success=False,
                configured=False,
                message="未配置 API Key，请在 backend/.env 中填写 DEEPSEEK_API_KEY 后再检测。",
                model_id=s.deepseek_model_id,
            )

        base_url = (s.deepseek_api_base_url or "").rstrip("/")
        url = f"{base_url}/chat/completions"
        payload = {
            "model": s.deepseek_model_id,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=s.model_request_timeout_seconds) as client:
                resp = client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            return ModelCheckResult(
                success=False,
                configured=True,
                message=sanitize_text(f"网络请求失败：{exc}", secret),
                model_id=s.deepseek_model_id,
            )

        if resp.status_code < 400:
            return ModelCheckResult(
                success=True,
                configured=True,
                message="连接成功：模型接口可正常响应。",
                model_id=s.deepseek_model_id,
            )

        # 接口返回错误（如模型 ID 无效、认证失败等），脱敏后原样反馈
        detail = sanitize_text(resp.text, secret)
        return ModelCheckResult(
            success=False,
            configured=True,
            message=f"接口返回错误（HTTP {resp.status_code}）：{detail}",
            model_id=s.deepseek_model_id,
        )
