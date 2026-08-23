"""阶段8本地完整联调状态；只返回脱敏能力与完整性汇总。"""
import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rbac import require_owner


ROOT = Path(__file__).resolve().parents[3]
REPORT_PATH = ROOT / "v2.0" / "stage-8-delivery" / "test-results.json"


def _database_health(db: Session) -> dict:
    try:
        migration = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
        integrity = db.execute(text("PRAGMA integrity_check")).scalar_one_or_none()
        foreign_key_errors = len(db.execute(text("PRAGMA foreign_key_check")).all())
        return {
            "migration": migration or "unknown",
            "integrity": integrity or "unknown",
            "foreign_key_errors": foreign_key_errors,
        }
    except Exception:  # noqa: BLE001 - 状态接口必须脱敏，禁止回传数据库异常正文
        return {"migration": "unknown", "integrity": "error", "foreign_key_errors": None}


def status(db: Session) -> dict:
    require_owner()
    settings = get_settings()
    report = {"status": "未验证"}
    if REPORT_PATH.exists():
        try:
            report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            report = {"status": "报告暂不可读"}
    verified = report.get("status") == "通过"
    reported_capabilities = report.get("capabilities", {}) if verified else {}
    capability_names = (
        "stage1_to_7_regression",
        "multi_day_and_cross_device",
        "network_failure_recovery",
        "model_and_index_degrade",
        "backup_restore_rehearsal",
        "responsive_desktop_mobile",
        "security_headers",
        "accessibility_baseline",
    )
    return {
        "stage": 8,
        "database": _database_health(db),
        "capabilities": {
            name: reported_capabilities.get(name) is True for name in capability_names
        },
        "runtime_boundaries": {
            "real_model_enabled": settings.enable_v2_real_model,
            "real_model_effective": settings.enable_v2_real_model and settings.is_model_configured,
            "external_embedding": False,
            "external_message_send": False,
            "public_deployment": False,
            "production_authentication": False,
            "local_dev_identity": settings.local_dev_owner_enabled,
        },
        "test_results": report,
    }
