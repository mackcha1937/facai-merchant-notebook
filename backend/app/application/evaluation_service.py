"""阶段7：离线 JSONL 测评登记、人工评分与发布/回滚门禁。

本模块不引用 ChatModel、不联网，也不把“已登记”伪装成“已执行”。JSONL
用例会形成不可变快照；未导入完整证据和人工评分前保持 blocked。
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.rbac import require_admin, require_owner
from app.core.tenant import get_current_owner_id, get_current_role, get_current_tenant_id
from app.domain.errors import ConflictError, DomainError, NotFoundError
from app.infrastructure.models import (
    AIConfigDraft,
    EvaluationCaseResult,
    EvaluationRun,
    PromptRelease,
    RagRelease,
    RecommendationRelease,
    ReleaseAudit,
    utcnow,
)

ROOT = Path(__file__).resolve().parents[3]
EVAL_PATH = ROOT / "v2.0" / "facai-v2-development-package" / "eval" / "ai-evaluation-cases.jsonl"
RUNNER_VERSION = "stage7-jsonl-manifest-v2"
RELEASE_MODELS = {
    "prompt": PromptRelease,
    "rag": RagRelease,
    "recommendation": RecommendationRelease,
}
SECRET_KEYS = {"api_key", "apikey", "secret", "token", "password", "authorization"}
SCORE_FIELDS = ("factual", "safety", "natural", "interaction")


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load(value: str | None, fallback):
    try:
        return json.loads(value) if value else fallback
    except (TypeError, json.JSONDecodeError):
        return fallback


def _checksum(value) -> str:
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _cases() -> list[dict]:
    rows = []
    required = {
        "case_id", "category", "priority", "title", "expected_behavior",
        "forbidden_behavior", "auto_assertions", "safety_critical",
    }
    for line_number, line in enumerate(EVAL_PATH.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not required.issubset(row) or not isinstance(row["safety_critical"], bool):
            raise DomainError(f"测评集第{line_number}行结构无效")
        if not isinstance(row["auto_assertions"], list):
            raise DomainError(f"测评集第{line_number}行auto_assertions无效")
        rows.append(row)
    ids = [row["case_id"] for row in rows]
    if not rows or len(ids) != len(set(ids)):
        raise DomainError("测评集为空或case_id重复")
    return rows


def _reject_secrets(value, path="content") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower().replace("-", "_") in SECRET_KEYS:
                raise DomainError(f"配置草稿禁止包含秘密字段：{path}.{key}")
            _reject_secrets(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_secrets(child, f"{path}[{index}]")


def create_draft(db: Session, data) -> dict:
    require_admin()
    _reject_secrets(data.content)
    if not data.content:
        raise DomainError("配置草稿不能为空")
    checksum = _checksum(data.content)
    row = AIConfigDraft(
        tenant_id=get_current_tenant_id(),
        config_type=data.config_type,
        content_json=_json(data.content),
        content_checksum=checksum,
        data_version=1,
        status="draft",
        created_by=get_current_owner_id(),
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _draft_view(row)


def _draft_view(row: AIConfigDraft) -> dict:
    content = _load(row.content_json, {})
    checksum = row.content_checksum or _checksum(content)
    return {
        "id": row.id,
        "config_type": row.config_type,
        "status": row.status,
        "checksum": checksum,
        "data_version": row.data_version,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def list_drafts(db: Session) -> list[dict]:
    require_admin()
    rows = db.scalars(
        select(AIConfigDraft)
        .where(AIConfigDraft.tenant_id == get_current_tenant_id())
        .order_by(AIConfigDraft.id.desc())
    ).all()
    return [_draft_view(row) for row in rows]


def start_run(db: Session, data) -> dict:
    require_admin()
    tenant = get_current_tenant_id()
    existing = db.scalar(
        select(EvaluationRun).where(
            EvaluationRun.tenant_id == tenant,
            EvaluationRun.run_key == data.idempotency_key,
        )
    )
    if existing is not None:
        if existing.draft_id != data.draft_id:
            raise ConflictError("该测评幂等键已用于其他草稿")
        return run_detail(db, existing.id)

    draft = db.scalar(
        select(AIConfigDraft).where(AIConfigDraft.id == data.draft_id, AIConfigDraft.tenant_id == tenant)
    )
    if draft is None:
        raise NotFoundError("配置草稿不存在")
    if draft.status not in {"draft", "evaluated", "blocked"}:
        raise ConflictError("该草稿当前不能重新测评")

    cases = _cases()
    now = utcnow()
    suite_checksum = _checksum(cases)
    config_checksum = draft.content_checksum or _checksum(_load(draft.content_json, {}))
    snapshot = {
        "draft_id": draft.id,
        "config_type": draft.config_type,
        "config_checksum": config_checksum,
        "case_source": str(EVAL_PATH.relative_to(ROOT)),
        "case_checksum": suite_checksum,
        "case_count": len(cases),
        "runner": RUNNER_VERSION,
        "execution_status": "awaiting_runtime_and_manual_evidence",
        "external_calls": 0,
    }
    run = EvaluationRun(
        tenant_id=tenant,
        draft_id=draft.id,
        created_by=get_current_owner_id(),
        suite_checksum=suite_checksum,
        runner_version=RUNNER_VERSION,
        run_key=data.idempotency_key,
        status="running",
        config_snapshot_json=_json(snapshot),
        started_at=now,
        created_at=now,
    )
    db.add(run)
    db.flush()
    for case in cases:
        expected = {
            "title": case["title"],
            "expected_behavior": case["expected_behavior"],
            "forbidden_behavior": case["forbidden_behavior"],
            "auto_assertions": case["auto_assertions"],
            "manual_rubric": case.get("manual_rubric", ""),
        }
        db.add(EvaluationCaseResult(
            tenant_id=tenant,
            run_id=run.id,
            case_id=case["case_id"],
            category=case["category"],
            priority=case["priority"],
            safety_critical=case["safety_critical"],
            expected_json=_json(expected),
            output_json=_json({
                "status": "blocked",
                "reason": "awaiting_runtime_and_manual_evidence",
            }),
            assertion_results_json=_json([
                {"assertion": assertion, "status": "blocked"}
                for assertion in case["auto_assertions"]
            ]),
            passed=None,
            created_at=now,
            updated_at=now,
        ))
    run.status = "blocked"
    run.finished_at = utcnow()
    draft.status = "blocked"
    draft.updated_at = utcnow()
    db.commit()
    return run_detail(db, run.id)


def _round_average(values: list[int]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def _summary(results: list[EvaluationCaseResult]) -> dict:
    total = len(results)
    passed = sum(row.passed is True for row in results)
    failed = sum(row.passed is False for row in results)
    blocked = total - passed - failed
    critical = [row for row in results if row.safety_critical]
    averages = {
        field: _round_average([
            value for row in results
            if (value := getattr(row, f"{field}_score")) is not None
        ])
        for field in SCORE_FIELDS
    }
    quality_gate = all(value is not None and value >= 4.0 for value in averages.values())
    safety_passed = sum(row.passed is True for row in critical)
    release_allowed = bool(
        total
        and blocked == 0
        and failed == 0
        and safety_passed == len(critical)
        and quality_gate
    )
    gate = "passed" if release_allowed else ("failed" if failed else "blocked")
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "blocked": blocked,
        "safety_total": len(critical),
        "safety_passed": safety_passed,
        "manual_averages": averages,
        "quality_gate": quality_gate,
        "gate_status": gate,
        "release_allowed": release_allowed,
    }


def _get_run(db: Session, run_id: int) -> EvaluationRun:
    run = db.scalar(select(EvaluationRun).where(
        EvaluationRun.id == run_id,
        EvaluationRun.tenant_id == get_current_tenant_id(),
    ))
    if run is None:
        raise NotFoundError("测评Run不存在")
    return run


def _run_results(db: Session, run_id: int) -> list[EvaluationCaseResult]:
    return list(db.scalars(
        select(EvaluationCaseResult).where(
            EvaluationCaseResult.run_id == run_id,
            EvaluationCaseResult.tenant_id == get_current_tenant_id(),
        ).order_by(EvaluationCaseResult.case_id)
    ).all())


def run_detail(db: Session, run_id: int) -> dict:
    require_admin()
    run = _get_run(db, run_id)
    results = _run_results(db, run.id)
    return {
        "id": run.id,
        "draft_id": run.draft_id,
        "status": run.status,
        "runner_version": run.runner_version,
        "snapshot": _load(run.config_snapshot_json, {}),
        "summary": _summary(results),
        "results": [{
            "case_id": row.case_id,
            "category": row.category,
            "priority": row.priority,
            "safety_critical": row.safety_critical,
            "passed": row.passed,
            "expected": _load(row.expected_json, {}),
            "assertions": _load(row.assertion_results_json, []),
            **_load(row.output_json, {}),
        } for row in results],
        "external_calls": 0,
    }


def list_runs(db: Session) -> list[dict]:
    require_admin()
    ids = db.scalars(
        select(EvaluationRun.id)
        .where(EvaluationRun.tenant_id == get_current_tenant_id())
        .order_by(EvaluationRun.id.desc())
    ).all()
    return [run_detail(db, value) for value in ids]


def export_csv(db: Session, run_id: int) -> str:
    detail = run_detail(db, run_id)
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(["case_id", "passed", "factual", "safety", "natural", "interaction", "notes"])
    for row in detail["results"]:
        writer.writerow([row["case_id"], "", "", "", "", "", ""])
    return "\ufeff" + stream.getvalue()


def _parse_score(case_id: str, field: str, value: str | None) -> int:
    raw = (value or "").strip()
    try:
        score = int(raw)
    except ValueError as exc:
        raise DomainError(f"{case_id}的{field}必须为1到5的整数") from exc
    if score < 1 or score > 5:
        raise DomainError(f"{case_id}的{field}必须为1到5的整数")
    return score


def _validate_csv(text: str, expected: set[str]) -> dict[str, dict]:
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    required = {"case_id", "passed", *SCORE_FIELDS, "notes"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise DomainError("CSV缺少case_id、passed、评分或notes列")
    validated = {}
    for item in reader:
        case_id = (item.get("case_id") or "").strip()
        if case_id not in expected or case_id in validated:
            raise DomainError(f"未知或重复case_id：{case_id}")
        raw_passed = (item.get("passed") or "").strip().lower()
        if raw_passed not in {"true", "false"}:
            raise DomainError(f"{case_id}的passed必须为true或false")
        validated[case_id] = {
            "passed": raw_passed == "true",
            "scores": {field: _parse_score(case_id, field, item.get(field)) for field in SCORE_FIELDS},
            "notes": (item.get("notes") or "").strip()[:2000],
        }
    if set(validated) != expected:
        raise DomainError(f"人工结果不完整：缺少{len(expected - set(validated))}条")
    return validated


def import_csv(db: Session, run_id: int, text: str) -> dict:
    require_admin()
    run = _get_run(db, run_id)
    results = _run_results(db, run.id)
    expected = {row.case_id for row in results}
    validated = _validate_csv(text, expected)
    draft = db.scalar(select(AIConfigDraft).where(
        AIConfigDraft.id == run.draft_id,
        AIConfigDraft.tenant_id == get_current_tenant_id(),
    ))
    if draft is None:
        raise NotFoundError("测评草稿不存在")
    if draft.status == "published":
        raise ConflictError("已发布草稿不能覆盖测评结果")

    now = utcnow()
    for result in results:
        value = validated[result.case_id]
        result.passed = value["passed"]
        result.factual_score = value["scores"]["factual"]
        result.safety_score = value["scores"]["safety"]
        result.natural_score = value["scores"]["natural"]
        result.interaction_score = value["scores"]["interaction"]
        result.notes = value["notes"]
        result.output_json = _json({
            "status": "passed" if value["passed"] else "failed",
            "evidence_source": "complete_manual_csv_import",
            "manual_scores": value["scores"],
            "notes": value["notes"],
        })
        result.assertion_results_json = _json([
            {**assertion, "status": "manually_verified" if value["passed"] else "failed"}
            for assertion in _load(result.assertion_results_json, [])
        ])
        result.updated_at = now

    summary = _summary(results)
    run.status = summary["gate_status"]
    run.finished_at = now
    snapshot = _load(run.config_snapshot_json, {})
    snapshot["manual_import_checksum"] = hashlib.sha256(text.encode()).hexdigest()
    snapshot["summary"] = summary
    snapshot["execution_status"] = "complete_manual_evidence_imported"
    run.config_snapshot_json = _json(snapshot)
    draft.status = "evaluated" if summary["release_allowed"] else "blocked"
    draft.updated_at = now
    db.commit()
    return run_detail(db, run_id)


def _existing_audit_response(
    db: Session, action: str, idempotency_key: str, expected: dict,
) -> dict | None:
    audit = db.scalar(select(ReleaseAudit).where(
        ReleaseAudit.tenant_id == get_current_tenant_id(),
        ReleaseAudit.idempotency_key == idempotency_key,
    ))
    if audit is None:
        return None
    if audit.action != action:
        raise ConflictError("该发布幂等键已用于其他操作")
    response = _load(audit.after_json, {})
    if any(response.get(key) != value for key, value in expected.items()):
        raise ConflictError("该发布幂等键已用于其他目标")
    return response


def publish(db: Session, data) -> dict:
    require_admin()
    replay = _existing_audit_response(db, "publish", data.idempotency_key, {
        "source_draft_id": data.draft_id,
        "evaluation_run_id": data.run_id,
    })
    if replay is not None:
        return {**replay, "idempotent_replay": True}

    detail = run_detail(db, data.run_id)
    if detail["draft_id"] != data.draft_id or not detail["summary"]["release_allowed"]:
        raise ConflictError("测评门槛未通过，禁止发布")
    tenant = get_current_tenant_id()
    run = _get_run(db, data.run_id)
    draft = db.scalar(select(AIConfigDraft).where(
        AIConfigDraft.id == data.draft_id,
        AIConfigDraft.tenant_id == tenant,
    ))
    if draft is None:
        raise NotFoundError("配置草稿不存在")
    if draft.data_version != data.expected_data_version:
        raise ConflictError("配置草稿版本已变化，请刷新后重试", {
            "current_data_version": draft.data_version,
        })
    content = _load(draft.content_json, {})
    checksum = _checksum(content)
    snapshot = _load(run.config_snapshot_json, {})
    if snapshot.get("config_checksum") != checksum:
        raise ConflictError("草稿内容已变化，必须重新测评")
    expected_confirmation = f"PUBLISH-{draft.id}-{checksum[:8]}"
    if data.confirmation != expected_confirmation:
        raise DomainError(f"二次确认文本不匹配，应为{expected_confirmation}")
    already_released = db.scalar(select(RELEASE_MODELS[draft.config_type]).where(
        RELEASE_MODELS[draft.config_type].tenant_id == tenant,
        RELEASE_MODELS[draft.config_type].evaluation_run_id == run.id,
    ))
    if already_released is not None:
        raise ConflictError("该测评Run已发布，不能重复创建版本")

    model = RELEASE_MODELS[draft.config_type]
    previous = db.scalar(select(model).where(
        model.tenant_id == tenant,
        model.status == "published",
    ).order_by(model.version.desc()).limit(1))
    if previous:
        previous.status = "superseded"
        if previous.source_draft_id:
            previous_draft = db.scalar(select(AIConfigDraft).where(
                AIConfigDraft.id == previous.source_draft_id,
                AIConfigDraft.tenant_id == tenant,
            ))
            if previous_draft:
                previous_draft.status = "superseded"
                previous_draft.data_version += 1
                previous_draft.updated_at = utcnow()
    version = (db.scalar(select(func.max(model.version)).where(model.tenant_id == tenant)) or 0) + 1
    release = model(
        tenant_id=tenant,
        version=version,
        config_snapshot_json=draft.content_json,
        source_draft_id=draft.id,
        evaluation_run_id=run.id,
        published_by=get_current_owner_id(),
        status="published",
        published_at=utcnow(),
        created_at=utcnow(),
    )
    db.add(release)
    db.flush()
    draft.status = "published"
    draft.data_version += 1
    draft.updated_at = utcnow()
    response = {
        "release_type": draft.config_type,
        "release_id": release.id,
        "version": version,
        "status": "published",
        "source_draft_id": draft.id,
        "evaluation_run_id": run.id,
        "external_calls": 0,
        "idempotent_replay": False,
    }
    db.add(ReleaseAudit(
        tenant_id=tenant,
        release_type=draft.config_type,
        release_id=release.id,
        actor_id=get_current_owner_id(),
        action="publish",
        request_id=data.request_id,
        idempotency_key=data.idempotency_key,
        before_json=_json({"previous_release_id": previous.id if previous else None}),
        after_json=_json(response),
        created_at=utcnow(),
    ))
    db.commit()
    return response


def rollback(db: Session, data) -> dict:
    require_admin()
    replay = _existing_audit_response(db, "rollback", data.idempotency_key, {
        "release_type": data.release_type,
        "rolled_back_id": data.release_id,
    })
    if replay is not None:
        return {**replay, "idempotent_replay": True}
    tenant = get_current_tenant_id()
    model = RELEASE_MODELS[data.release_type]
    current = db.scalar(select(model).where(
        model.id == data.release_id,
        model.tenant_id == tenant,
        model.status == "published",
    ))
    if current is None:
        raise NotFoundError("当前发布版本不存在")
    expected_confirmation = f"ROLLBACK-{data.release_type}-{current.id}"
    if data.confirmation != expected_confirmation:
        raise DomainError(f"二次确认文本不匹配，应为{expected_confirmation}")
    previous = db.scalar(select(model).where(
        model.tenant_id == tenant,
        model.status == "superseded",
        model.version < current.version,
    ).order_by(model.version.desc()).limit(1))
    if previous is None:
        raise ConflictError("没有可回滚的上一版本")
    current.status = "rolled_back"
    current.rolled_back_at = utcnow()
    previous.status = "published"
    previous.published_at = utcnow()
    current_draft = db.scalar(select(AIConfigDraft).where(
        AIConfigDraft.id == current.source_draft_id,
        AIConfigDraft.tenant_id == tenant,
    )) if current.source_draft_id else None
    previous_draft = db.scalar(select(AIConfigDraft).where(
        AIConfigDraft.id == previous.source_draft_id,
        AIConfigDraft.tenant_id == tenant,
    )) if previous.source_draft_id else None
    if current_draft:
        current_draft.status = "rolled_back"
        current_draft.data_version += 1
        current_draft.updated_at = utcnow()
    if previous_draft:
        previous_draft.status = "published"
        previous_draft.data_version += 1
        previous_draft.updated_at = utcnow()
    response = {
        "release_type": data.release_type,
        "status": "rolled_back",
        "rolled_back_id": current.id,
        "restored_release_id": previous.id,
        "restored_version": previous.version,
        "external_calls": 0,
        "idempotent_replay": False,
    }
    db.add(ReleaseAudit(
        tenant_id=tenant,
        release_type=data.release_type,
        release_id=current.id,
        actor_id=get_current_owner_id(),
        action="rollback",
        request_id=data.request_id,
        idempotency_key=data.idempotency_key,
        before_json=_json({"release_id": current.id, "version": current.version}),
        after_json=_json(response),
        created_at=utcnow(),
    ))
    db.commit()
    return response


def list_releases(db: Session) -> dict[str, list[dict]]:
    require_admin()
    tenant = get_current_tenant_id()
    output = {}
    for release_type, model in RELEASE_MODELS.items():
        rows = db.scalars(select(model).where(
            model.tenant_id == tenant,
        ).order_by(model.version.desc())).all()
        rollback_available = {
            row.id: row.status == "published" and any(
                candidate.status == "superseded" and candidate.version < row.version
                for candidate in rows
            )
            for row in rows
        }
        output[release_type] = [{
            "id": row.id,
            "version": row.version,
            "status": row.status,
            "source_draft_id": row.source_draft_id,
            "evaluation_run_id": row.evaluation_run_id,
            "published_at": row.published_at.isoformat() if row.published_at else None,
            "rolled_back_at": row.rolled_back_at.isoformat() if row.rolled_back_at else None,
            "rollback_available": rollback_available[row.id],
            "rollback_confirmation": (
                f"ROLLBACK-{release_type}-{row.id}" if rollback_available[row.id] else None
            ),
        } for row in rows]
    return output


def list_audits(db: Session) -> list[dict]:
    require_admin()
    rows = db.scalars(select(ReleaseAudit).where(
        ReleaseAudit.tenant_id == get_current_tenant_id(),
    ).order_by(ReleaseAudit.id.desc()).limit(100)).all()
    return [{
        "id": row.id,
        "release_type": row.release_type,
        "release_id": row.release_id,
        "actor_id": row.actor_id,
        "action": row.action,
        "request_id": row.request_id,
        "created_at": row.created_at.isoformat(),
    } for row in rows]


def status(db: Session) -> dict:
    require_owner()
    tenant = get_current_tenant_id()
    latest = db.scalar(select(EvaluationRun).where(
        EvaluationRun.tenant_id == tenant,
    ).order_by(EvaluationRun.id.desc()).limit(1))
    release_counts = {
        name: db.scalar(select(func.count(model.id)).where(
            model.tenant_id == tenant,
            model.status == "published",
        )) or 0
        for name, model in RELEASE_MODELS.items()
    }
    latest_summary = None
    if latest and get_current_role() == "admin":
        latest_summary = _summary(_run_results(db, latest.id))
    return {
        "latest_run": latest_summary,
        "published": release_counts,
        "real_model_calls": 0,
        "external_calls": 0,
        "capabilities": {
            "jsonl_manifest_runner": True,
            "automatic_runtime_executor": False,
            "manual_csv_roundtrip": True,
            "safety_gate": True,
            "quality_score_gate": True,
            "two_step_publish": True,
            "rollback": True,
            "idempotent_audit": True,
        },
    }
