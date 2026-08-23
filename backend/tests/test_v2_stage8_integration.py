"""阶段8安全响应头、最终状态与SQLite备份恢复验收。"""
import json
import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from app.core.tenant import set_current_owner_id, set_current_role, set_current_tenant_id
from scripts.stage8_restore_verify import restore_and_verify


BACKEND_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def owner_context():
    set_current_tenant_id(1); set_current_owner_id(1); set_current_role("owner")
    yield
    set_current_tenant_id(None); set_current_owner_id(None); set_current_role(None)


def test_security_headers_api_no_store_spa_csp_and_https_hsts(client):
    api_response = client.get("/api/health")
    assert api_response.status_code == 200
    assert api_response.headers["x-content-type-options"] == "nosniff"
    assert api_response.headers["x-frame-options"] == "DENY"
    assert api_response.headers["referrer-policy"] == "no-referrer"
    assert api_response.headers["permissions-policy"] == "camera=(), geolocation=(), microphone=(self)"
    assert api_response.headers["cache-control"] == "no-store"
    assert "strict-transport-security" not in api_response.headers

    spa_response = client.get("/verify/v2-stage-8")
    assert "frame-ancestors 'none'" in spa_response.headers["content-security-policy"]
    https_response = client.get("https://testserver/api/health")
    assert https_response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"


def test_stage8_status_is_sanitized_honest_and_owner_readable(client, monkeypatch, tmp_path):
    response = client.get("/api/v2-stage8/status")
    assert response.status_code == 200
    body = response.json()
    assert body["stage"] == 8
    assert body["database"]["integrity"] in {"ok", "error"}
    assert body["runtime_boundaries"]["real_model_effective"] is False
    assert body["runtime_boundaries"]["external_embedding"] is False
    assert body["runtime_boundaries"]["external_message_send"] is False
    assert body["runtime_boundaries"]["public_deployment"] is False
    assert body["runtime_boundaries"]["production_authentication"] is False
    serialized = json.dumps(body).lower()
    assert "deepseek_api_key" not in serialized and "sk-" not in serialized

    from app.application import stage8_service
    monkeypatch.setattr(stage8_service, "REPORT_PATH", tmp_path / "missing-report.json")
    missing_report = client.get("/api/v2-stage8/status").json()
    assert not any(missing_report["capabilities"].values())


def test_stage8_status_fails_closed_without_identity_context(client, monkeypatch):
    from app.core.config import get_settings

    set_current_tenant_id(None); set_current_owner_id(None); set_current_role(None)
    monkeypatch.setattr(get_settings(), "local_dev_owner_enabled", False)
    response = client.get("/api/v2-stage8/status")
    assert response.status_code == 400
    assert "缺少" in response.json()["detail"]


def test_sqlite_online_backup_restore_digest_integrity_and_no_overwrite(tmp_path):
    source = tmp_path / "source.db"
    restored = tmp_path / "restored.db"
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{source}")
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.upgrade(cfg, "head")
    connection = sqlite3.connect(source)
    connection.execute("INSERT INTO customers (tenant_id,display_name) VALUES (1,'虚构恢复验收顾客')")
    connection.commit(); connection.close()

    result = restore_and_verify(source, restored)
    assert result["status"] == "通过"
    assert result["migration"] == "0020_stage7_evaluation_release"
    assert result["integrity"] == "ok" and result["foreign_key_errors"] == 0
    assert result["source_digest"] == result["restored_digest"]
    with pytest.raises(FileExistsError, match="拒绝覆盖"):
        restore_and_verify(source, restored)
