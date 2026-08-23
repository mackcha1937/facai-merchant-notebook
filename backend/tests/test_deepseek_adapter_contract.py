"""DeepSeek V4 请求协议测试：全部使用 MockTransport，禁止真实网络。"""
import json
from types import SimpleNamespace

import httpx
import pytest

from app.infrastructure.llm import deepseek as deepseek_module
from app.infrastructure.llm.base import ModelError
from app.infrastructure.llm.deepseek import DeepSeekAdapter


SECRET = "contract-test-secret-value"


def _settings():
    return SimpleNamespace(
        deepseek_api_base_url="https://api.deepseek.com",
        deepseek_model_id="deepseek-v4-pro",
        deepseek_api_key=SECRET,
        model_request_timeout_seconds=30.0,
        is_model_configured=True,
    )


def _install_transport(monkeypatch, handler):
    real_client = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        deepseek_module.httpx,
        "Client",
        lambda **kwargs: real_client(transport=transport, **kwargs),
    )


def test_chat_sends_v4_json_non_thinking_contract_without_exposing_key(monkeypatch):
    captured = {}

    def handler(request: httpx.Request):
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["Authorization"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"intent":"unknown"}'}}]},
        )

    _install_transport(monkeypatch, handler)
    messages = [
        {"role": "system", "content": "只输出 JSON object。"},
        {"role": "user", "content": "测试输入"},
    ]

    result = DeepSeekAdapter(settings=_settings()).chat(messages, temperature=0.0)

    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["authorization"] == f"Bearer {SECRET}"
    assert captured["payload"] == {
        "model": "deepseek-v4-pro",
        "messages": messages,
        "response_format": {"type": "json_object"},
        "thinking": {"type": "disabled"},
        "temperature": 0.0,
        "max_tokens": 2000,
        "stream": False,
    }
    assert result == '{"intent":"unknown"}'
    assert SECRET not in result


def test_chat_sanitizes_key_from_http_error(monkeypatch):
    def handler(_request: httpx.Request):
        return httpx.Response(401, text=f"Authorization rejected for {SECRET}")

    _install_transport(monkeypatch, handler)

    with pytest.raises(ModelError) as captured:
        DeepSeekAdapter(settings=_settings()).chat(
            [{"role": "system", "content": "只输出 JSON object。"}],
            temperature=0.0,
        )

    message = str(captured.value)
    assert "HTTP 401" in message
    assert SECRET not in message
    assert "***" in message
