"""模型配置与适配器测试（不依赖真实网络和 API Key）。"""
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.infrastructure.llm.deepseek import DeepSeekAdapter
from app.main import app

client = TestClient(app)


def _fake_settings(**overrides):
    base = dict(
        deepseek_api_base_url="https://api.deepseek.com",
        deepseek_model_id="deepseek-v4-pro",
        deepseek_api_key="",
        model_request_timeout_seconds=30.0,
        is_model_configured=False,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_adapter_returns_not_configured_without_key():
    adapter = DeepSeekAdapter(settings=_fake_settings())
    result = adapter.check_connectivity()
    assert result.configured is False
    assert result.success is False


def test_model_status_does_not_expose_key():
    app.dependency_overrides[get_settings] = lambda: _fake_settings()
    try:
        resp = client.get("/api/config/model-status")
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 200
    body = resp.json()
    assert body["configured"] is False
    assert "api_key" not in body
    assert "DEEPSEEK_API_KEY" not in str(body)


def test_model_check_without_key():
    app.dependency_overrides[get_settings] = lambda: _fake_settings()
    try:
        resp = client.post("/api/model/check")
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 200
    body = resp.json()
    assert body["configured"] is False
    assert body["success"] is False
    assert "api_key" not in body
