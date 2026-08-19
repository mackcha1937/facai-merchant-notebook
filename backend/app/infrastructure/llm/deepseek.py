"""DeepSeek 模型适配器（OpenAI 兼容接口）。

所有对外暴露的错误信息都经过脱敏，不包含 API Key。
"""
import httpx

from app.core.logging import sanitize_text
from app.infrastructure.llm.base import ModelAdapter, ModelCheckResult, ModelError


class DeepSeekAdapter(ModelAdapter):
    def __init__(self, settings=None):
        if settings is None:
            from app.core.config import get_settings

            settings = get_settings()
        self.settings = settings

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.settings.deepseek_api_key}",
            "Content-Type": "application/json",
        }

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

        try:
            with httpx.Client(timeout=s.model_request_timeout_seconds) as client:
                resp = client.post(url, json=payload, headers=self._headers())
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

        detail = sanitize_text(resp.text, secret)
        return ModelCheckResult(
            success=False,
            configured=True,
            message=f"接口返回错误（HTTP {resp.status_code}）：{detail}",
            model_id=s.deepseek_model_id,
        )

    def chat(self, messages: list[dict], temperature: float = 0.0) -> str:
        s = self.settings
        secret = getattr(s, "deepseek_api_key", "") or ""

        if not s.is_model_configured:
            raise ModelError("未配置 API Key，请在 backend/.env 中填写 DEEPSEEK_API_KEY。")

        base_url = (s.deepseek_api_base_url or "").rstrip("/")
        url = f"{base_url}/chat/completions"
        payload = {
            "model": s.deepseek_model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 2000,
            "stream": False,
        }

        try:
            with httpx.Client(timeout=s.model_request_timeout_seconds) as client:
                resp = client.post(url, json=payload, headers=self._headers())
        except httpx.HTTPError as exc:
            raise ModelError(sanitize_text(f"模型网络请求失败：{exc}", secret)) from exc

        if resp.status_code >= 400:
            detail = sanitize_text(resp.text, secret)
            raise ModelError(f"模型接口错误（HTTP {resp.status_code}）：{detail}")

        try:
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ModelError("模型返回格式异常，无法读取回复内容。") from exc
