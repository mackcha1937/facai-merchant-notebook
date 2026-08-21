"""提示词版本管理接口测试。"""
import pytest

from app.core.tenant import set_current_role


@pytest.fixture(autouse=True)
def _admin_role():
    set_current_role("admin")
    yield
    set_current_role(None)


def test_get_current_prompt_initialized(client):
    resp = client.get("/api/settings/prompt")
    assert resp.status_code == 200
    body = resp.json()
    assert body["version"] == 1
    assert "JSON" in body["content"]
    assert "model_id" in body
    assert "api_key" not in str(body).lower()


def test_save_then_activate(client):
    resp = client.post(
        "/api/settings/prompt/versions",
        json={"content": "你是解析器。请只输出符合 Schema 的 JSON。"},
    )
    assert resp.status_code == 201
    v2 = resp.json()
    assert v2["version"] == 2
    assert v2["is_active"] is False

    activate = client.post(f"/api/settings/prompt/versions/{v2['id']}/activate")
    assert activate.status_code == 200

    current = client.get("/api/settings/prompt").json()
    assert current["version"] == 2


def test_rollback_to_previous_version(client):
    versions = client.get("/api/settings/prompt/versions").json()
    v1 = versions[-1]  # 最早的版本（version=1）
    resp = client.post(f"/api/settings/prompt/versions/{v1['id']}/activate")
    assert resp.status_code == 200
    current = client.get("/api/settings/prompt").json()
    assert current["version"] == 1


def test_empty_content_rejected(client):
    resp = client.post("/api/settings/prompt/versions", json={"content": "   "})
    assert resp.status_code == 400


def test_missing_json_instruction_rejected(client):
    resp = client.post("/api/settings/prompt/versions", json={"content": "随便写点东西"})
    assert resp.status_code == 400
