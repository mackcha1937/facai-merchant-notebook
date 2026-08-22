"""V2 阶段2：双端应用壳与 Mock 交互闭环验证接口（受开发开关保护）。

- 仅在 ENABLE_STAGE2_VERIFY=true 时允许调用，生产默认关闭；
- 只读，不写入真实 SQLite 业务表；
- 不返回真实客户姓名、手机号、微信名或 API Key；
- mock-speech 只返回可编辑文本，不执行任何业务写入。
"""
import hashlib
import sqlite3

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import BACKEND_ROOT, get_settings
from app.infrastructure.stt import MockSpeechToTextAdapter, SttError

router = APIRouter(prefix="/api/v2/stage2", tags=["v2-stage2"])

# 阶段2 只读校验的 V1 权威表（不含新表，不返回姓名/手机号等敏感列）
_V1_CHECK_TABLES = [
    "customers",
    "customer_aliases",
    "services",
    "packages",
    "ledger_entries",
    "prompt_versions",
    "agent_proposals",
]


def _db():
    return sqlite3.connect(str(BACKEND_ROOT / "data" / "app.db"))


def _require_enabled():
    if not get_settings().enable_stage2_verify:
        raise HTTPException(status_code=403, detail="阶段2验证接口未开启（ENABLE_STAGE2_VERIFY=false）")


def _checksum(rows: list) -> str:
    return hashlib.sha256(repr(rows).encode("utf-8")).hexdigest()[:16]


def _v1_baseline(conn: sqlite3.Connection) -> dict:
    counts = {}
    checksums = {}
    for t in _V1_CHECK_TABLES:
        rows = conn.execute(f"SELECT * FROM {t} ORDER BY id").fetchall()
        counts[t] = len(rows)
        checksums[t] = _checksum(rows)
    return {
        "customer_count": conn.execute("SELECT COUNT(*) FROM customers WHERE deleted_at IS NULL").fetchone()[0],
        "package_count": conn.execute("SELECT COUNT(*) FROM packages WHERE deleted_at IS NULL").fetchone()[0],
        "ledger_count": conn.execute("SELECT COUNT(*) FROM ledger_entries WHERE deleted_at IS NULL").fetchone()[0],
        "counts": counts,
        "checksums": checksums,
    }


@router.get("/status")
def stage2_status():
    _require_enabled()
    conn = _db()
    try:
        version = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        baseline = _v1_baseline(conn)
        return {
            "migration_version": version,
            "is_mock": True,
            "mock_note": "当前为Mock交互，未接推荐、RAG和真实语音",
            "v1_baseline": baseline,
            "capabilities": {
                "mock_speech": True,
                "real_recommendation": False,
                "rag": False,
                "real_voice": False,
                "unified_proposal": False,
                "customer_fact_ai": False,
                "product_ai_recognition": False,
            },
        }
    finally:
        conn.close()


class MockSpeechRequest(BaseModel):
    utterance: str = ""
    scenario: str = "success"  # success | transcribe_failure | network_failure


@router.post("/mock-speech")
def mock_speech(req: MockSpeechRequest):
    """Mock 语音转写：只返回可编辑文本，不写入任何数据。"""
    _require_enabled()
    fail_mode = {
        "success": None,
        "transcribe_failure": "transcribe",
        "network_failure": "network",
    }.get(req.scenario, None)
    adapter = MockSpeechToTextAdapter(fail_mode=fail_mode)
    try:
        result = adapter.transcribe(req.utterance)
    except SttError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {
        "transcript": result.transcript,
        "confidence": result.confidence,
        "segments": [s.__dict__ for s in result.segments],
        "is_mock": result.is_mock,
        "audio_expires_in_seconds": result.audio_expires_in_seconds,
    }
