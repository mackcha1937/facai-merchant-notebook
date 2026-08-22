"""阶段2 后端测试：STT Mock 适配器、验证接口开关、V1 数据只读不变。"""
import sqlite3
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.config import BACKEND_ROOT
from app.infrastructure.stt import MockSpeechToTextAdapter, SttError
from app.main import app


@pytest.fixture(autouse=True)
def _reset():
    yield


def _client_enabled(monkeypatch, *, enabled=True):
    import app.api.routes.v2_stage2 as v2_stage2

    monkeypatch.setattr(v2_stage2, "get_settings", lambda: SimpleNamespace(enable_stage2_verify=enabled))
    return TestClient(app)


def _snapshot_v1_counts():
    conn = sqlite3.connect(str(BACKEND_ROOT / "data" / "app.db"))
    tables = ["customers", "customer_aliases", "services", "packages", "ledger_entries", "prompt_versions", "agent_proposals"]
    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
    conn.close()
    return counts


# ---------- Mock 转写适配器 ----------

def test_mock_stt_success_echo():
    adapter = MockSpeechToTextAdapter()
    result = adapter.transcribe("返回客户列表")
    assert result.transcript == "返回客户列表"
    assert result.is_mock is True
    assert result.provider == "mock"


def test_mock_stt_default_utterance():
    adapter = MockSpeechToTextAdapter()
    result = adapter.transcribe("")
    assert result.transcript


def test_mock_stt_transcribe_failure():
    adapter = MockSpeechToTextAdapter(fail_mode="transcribe")
    with pytest.raises(SttError):
        adapter.transcribe("随便说一句")


def test_mock_stt_network_failure():
    adapter = MockSpeechToTextAdapter(fail_mode="network")
    with pytest.raises(SttError):
        adapter.transcribe("随便说一句")


# ---------- 验证接口开关（ENABLE_STAGE2_VERIFY） ----------

def test_stage2_status_requires_enable_flag(monkeypatch):
    c = _client_enabled(monkeypatch, enabled=False)
    assert c.get("/api/v2/stage2/status").status_code == 403


def test_stage2_mock_speech_requires_enable_flag(monkeypatch):
    c = _client_enabled(monkeypatch, enabled=False)
    assert c.post("/api/v2/stage2/mock-speech", json={"utterance": "你好"}).status_code == 403


def test_stage2_status_reports_v1_baseline(monkeypatch):
    c = _client_enabled(monkeypatch, enabled=True)
    resp = c.get("/api/v2/stage2/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_mock"] is True
    baseline = body["v1_baseline"]
    assert "customer_count" in baseline and "package_count" in baseline and "ledger_count" in baseline
    assert "counts" in baseline and "checksums" in baseline
    caps = body["capabilities"]
    assert caps["mock_speech"] is True
    assert caps["real_recommendation"] is False
    assert caps["rag"] is False
    assert caps["real_voice"] is False


def test_stage2_mock_speech_success(monkeypatch):
    c = _client_enabled(monkeypatch, enabled=True)
    resp = c.post("/api/v2/stage2/mock-speech", json={"utterance": "日期改成昨天", "scenario": "success"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["transcript"] == "日期改成昨天"
    assert body["is_mock"] is True


def test_stage2_mock_speech_failure_scenarios(monkeypatch):
    c = _client_enabled(monkeypatch, enabled=True)
    assert c.post("/api/v2/stage2/mock-speech", json={"utterance": "x", "scenario": "transcribe_failure"}).status_code == 502
    assert c.post("/api/v2/stage2/mock-speech", json={"utterance": "x", "scenario": "network_failure"}).status_code == 502


# ---------- 阶段2 前后 V1 数据完全一致 ----------

def test_stage2_endpoints_do_not_write_v1(monkeypatch):
    before = _snapshot_v1_counts()
    c = _client_enabled(monkeypatch, enabled=True)
    c.get("/api/v2/stage2/status")
    c.post("/api/v2/stage2/mock-speech", json={"utterance": "小蓝今天做了一次肩颈按摩"})
    after = _snapshot_v1_counts()
    assert before == after, f"V1 数据被改动：before={before} after={after}"
