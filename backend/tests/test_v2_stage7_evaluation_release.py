"""阶段7离线测评、门禁、发布和回滚验收。"""
import csv
import io
import json

import pytest
from sqlalchemy import func, select

from app.api.routes import v2_stage7
from app.application import evaluation_service
from app.core.tenant import set_current_owner_id, set_current_role, set_current_tenant_id
from app.domain.errors import ConflictError, DomainError, NotFoundError
from app.infrastructure.models import (
    AIConfigDraft, EvaluationCaseResult, EvaluationRun, PromptRelease, ReleaseAudit,
)
from app.schemas.evaluation import (
    ConfigDraftCreate, EvaluationRunCreate, ReleasePublishRequest, ReleaseRollbackRequest,
)


@pytest.fixture(autouse=True)
def admin_context():
    set_current_tenant_id(1); set_current_owner_id(1); set_current_role("admin")
    yield
    set_current_tenant_id(None); set_current_owner_id(None); set_current_role(None)


def _completed_csv(exported: str, *, failed_case: str | None = None, score: str = "5") -> str:
    source = csv.DictReader(io.StringIO(exported.lstrip("\ufeff")))
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=source.fieldnames)
    writer.writeheader()
    for row in source:
        row.update({
            "passed": "false" if row["case_id"] == failed_case else "true",
            "factual": score,
            "safety": score,
            "natural": score,
            "interaction": score,
            "notes": "人工隔离验收",
        })
        writer.writerow(row)
    return output.getvalue()


def complete_run(db, config_type="prompt", version="v1", key="run-complete-v1"):
    draft = evaluation_service.create_draft(
        db, ConfigDraftCreate(config_type=config_type, content={"version": version, "temperature": 0}),
    )
    run = evaluation_service.start_run(
        db, EvaluationRunCreate(draft_id=draft["id"], idempotency_key=key),
    )
    assert run["summary"]["total"] == 60
    assert run["summary"]["blocked"] == 60
    assert run["summary"]["safety_total"] == 49
    completed = evaluation_service.import_csv(
        db, run["id"], _completed_csv(evaluation_service.export_csv(db, run["id"])),
    )
    assert completed["summary"]["passed"] == 60
    assert completed["summary"]["manual_averages"] == {
        "factual": 5.0, "safety": 5.0, "natural": 5.0, "interaction": 5.0,
    }
    assert completed["summary"]["release_allowed"] is True
    return draft, completed


def _publish_request(draft, run, *, key="publish-idempotency-v1", confirmation=None):
    return ReleasePublishRequest(
        draft_id=draft["id"],
        run_id=run["id"],
        confirmation=confirmation or f"PUBLISH-{draft['id']}-{draft['checksum'][:8]}",
        expected_data_version=draft["data_version"],
        request_id=f"request-{key}",
        idempotency_key=key,
    )


def test_jsonl_manifest_is_honest_blocked_versioned_and_idempotent(db_session):
    draft = evaluation_service.create_draft(
        db_session,
        ConfigDraftCreate(config_type="recommendation", content={"policy_version": "offline-v1"}),
    )
    request = EvaluationRunCreate(draft_id=draft["id"], idempotency_key="run-manifest-001")
    run = evaluation_service.start_run(db_session, request)
    replay = evaluation_service.start_run(db_session, request)
    assert replay["id"] == run["id"]
    assert run["runner_version"] == "stage7-jsonl-manifest-v2"
    assert run["snapshot"]["case_count"] == 60
    assert len(run["snapshot"]["case_checksum"]) == 64
    assert run["summary"]["blocked"] == 60 and run["summary"]["release_allowed"] is False
    assert run["results"][0]["assertions"][0]["status"] == "blocked"
    assert db_session.scalar(select(func.count(EvaluationCaseResult.id))) == 60
    assert db_session.scalar(select(func.count(EvaluationRun.id))) == 1
    with pytest.raises(ConflictError, match="门槛"):
        evaluation_service.publish(db_session, _publish_request(draft, run))


def test_manual_import_validates_every_row_and_is_atomic(db_session):
    draft = evaluation_service.create_draft(
        db_session, ConfigDraftCreate(config_type="rag", content={"retriever": "local"}),
    )
    run = evaluation_service.start_run(
        db_session, EvaluationRunCreate(draft_id=draft["id"], idempotency_key="run-import-001"),
    )
    with pytest.raises(DomainError, match="不完整"):
        evaluation_service.import_csv(
            db_session, run["id"],
            "case_id,passed,factual,safety,natural,interaction,notes\nINT-001,true,5,5,5,5,ok\n",
        )
    assert db_session.scalar(select(func.count(EvaluationCaseResult.id)).where(
        EvaluationCaseResult.passed.is_not(None),
    )) == 0

    invalid = _completed_csv(evaluation_service.export_csv(db_session, run["id"]), score="6")
    with pytest.raises(DomainError, match="1到5"):
        evaluation_service.import_csv(db_session, run["id"], invalid)
    assert db_session.scalar(select(func.count(EvaluationCaseResult.id)).where(
        EvaluationCaseResult.passed.is_not(None),
    )) == 0

    failed = _completed_csv(
        evaluation_service.export_csv(db_session, run["id"]), failed_case="PER-003",
    )
    result = evaluation_service.import_csv(db_session, run["id"], failed)
    assert result["summary"]["failed"] == 1
    assert result["summary"]["safety_passed"] == 48
    assert result["summary"]["release_allowed"] is False


def test_quality_average_below_four_blocks_release(db_session):
    draft = evaluation_service.create_draft(
        db_session, ConfigDraftCreate(config_type="prompt", content={"version": "low-score"}),
    )
    run = evaluation_service.start_run(
        db_session, EvaluationRunCreate(draft_id=draft["id"], idempotency_key="run-low-score"),
    )
    result = evaluation_service.import_csv(
        db_session, run["id"],
        _completed_csv(evaluation_service.export_csv(db_session, run["id"]), score="3"),
    )
    assert result["summary"]["passed"] == 60
    assert result["summary"]["quality_gate"] is False
    assert result["summary"]["release_allowed"] is False


def test_publish_is_bound_to_tested_checksum_version_and_idempotency(db_session):
    draft, run = complete_run(db_session, key="run-publish-v1")
    with pytest.raises(DomainError, match="二次确认"):
        evaluation_service.publish(db_session, _publish_request(
            draft, run, key="publish-wrong-confirm", confirmation="PUBLISH-wrong",
        ))
    with pytest.raises(ConflictError, match="版本已变化"):
        bad_version = _publish_request(draft, run, key="publish-bad-version")
        bad_version.expected_data_version = 99
        evaluation_service.publish(db_session, bad_version)

    row = db_session.get(AIConfigDraft, draft["id"])
    original = row.content_json
    row.content_json = json.dumps({"version": "changed-after-eval"})
    db_session.flush()
    with pytest.raises(ConflictError, match="重新测评"):
        evaluation_service.publish(db_session, _publish_request(draft, run, key="publish-stale"))
    row.content_json = original
    db_session.flush()

    request = _publish_request(draft, run)
    first = evaluation_service.publish(db_session, request)
    replay = evaluation_service.publish(db_session, request)
    assert first["evaluation_run_id"] == run["id"]
    assert replay["release_id"] == first["release_id"] and replay["idempotent_replay"] is True
    release = db_session.get(PromptRelease, first["release_id"])
    assert release.source_draft_id == draft["id"] and release.evaluation_run_id == run["id"]
    assert db_session.scalar(select(func.count(PromptRelease.id))) == 1
    assert db_session.scalar(select(func.count(ReleaseAudit.id))) == 1
    assert evaluation_service.list_releases(db_session)["prompt"][0]["rollback_available"] is False
    with pytest.raises(ConflictError, match="其他目标"):
        evaluation_service.publish(db_session, request.model_copy(update={"run_id": run["id"] + 999}))


def test_publish_second_version_and_idempotent_rollback_restore_previous(db_session):
    first_draft, first_run = complete_run(db_session, version="v1", key="run-release-first")
    first = evaluation_service.publish(
        db_session, _publish_request(first_draft, first_run, key="publish-release-first"),
    )
    second_draft, second_run = complete_run(db_session, version="v2", key="run-release-second")
    second = evaluation_service.publish(
        db_session, _publish_request(second_draft, second_run, key="publish-release-second"),
    )
    assert second["version"] == 2
    assert db_session.get(AIConfigDraft, first_draft["id"]).status == "superseded"
    assert db_session.get(AIConfigDraft, second_draft["id"]).status == "published"
    assert evaluation_service.list_releases(db_session)["prompt"][0]["rollback_available"] is True
    request = ReleaseRollbackRequest(
        release_type="prompt",
        release_id=second["release_id"],
        confirmation=f"ROLLBACK-prompt-{second['release_id']}",
        request_id="request-rollback-release-second",
        idempotency_key="rollback-release-second",
    )
    restored = evaluation_service.rollback(db_session, request)
    replay = evaluation_service.rollback(db_session, request)
    assert restored["restored_release_id"] == first["release_id"]
    assert replay["restored_release_id"] == first["release_id"] and replay["idempotent_replay"] is True
    assert db_session.get(PromptRelease, first["release_id"]).status == "published"
    assert db_session.get(AIConfigDraft, first_draft["id"]).status == "published"
    assert db_session.get(AIConfigDraft, second_draft["id"]).status == "rolled_back"
    assert db_session.scalar(select(func.count(ReleaseAudit.id))) == 3


def test_secret_fields_rbac_tenant_isolation_and_sanitized_views(client, db_session):
    with pytest.raises(DomainError, match="秘密字段"):
        evaluation_service.create_draft(
            db_session, ConfigDraftCreate(config_type="prompt", content={"api_key": "forbidden"}),
        )
    draft = evaluation_service.create_draft(
        db_session, ConfigDraftCreate(config_type="prompt", content={"version": "tenant1"}),
    )
    assert "content" not in evaluation_service.list_drafts(db_session)[0]
    set_current_role("owner")
    assert client.get("/api/admin/evaluations/drafts").status_code == 403
    owner_status = client.get("/api/v2-stage7/status")
    assert owner_status.status_code == 200 and owner_status.json()["latest_run"] is None
    assert owner_status.json()["capabilities"]["automatic_runtime_executor"] is False
    set_current_role("admin"); set_current_tenant_id(2); set_current_owner_id(2)
    assert evaluation_service.list_drafts(db_session) == []
    with pytest.raises(NotFoundError):
        evaluation_service.start_run(
            db_session, EvaluationRunCreate(draft_id=draft["id"], idempotency_key="tenant2-run-key"),
        )


def test_stage7_api_registers_jsonl_exports_utf8_and_lists_governance(client):
    route_pairs = [
        (route.path, method)
        for route in v2_stage7.router.routes
        for method in (getattr(route, "methods", None) or set())
    ]
    assert route_pairs.count(("/api/admin/evaluations/releases", "GET")) == 1
    assert route_pairs.count(("/api/admin/evaluations/releases/publish", "POST")) == 1
    assert route_pairs.count(("/api/admin/evaluations/releases/rollback", "POST")) == 1
    draft = client.post(
        "/api/admin/evaluations/drafts",
        json={"config_type": "recommendation", "content": {"version": "api-v1"}},
    )
    assert draft.status_code == 200
    run = client.post(
        "/api/admin/evaluations/runs",
        json={"draft_id": draft.json()["id"], "idempotency_key": "api-run-0001"},
    )
    assert run.status_code == 200 and run.json()["summary"]["total"] == 60
    exported = client.get(f"/api/admin/evaluations/runs/{run.json()['id']}/workbook.csv")
    assert exported.status_code == 200
    assert "case_id,passed" in exported.text
    assert "attachment" in exported.headers["content-disposition"]
    assert client.get("/api/admin/evaluations/releases").json() == {
        "prompt": [], "rag": [], "recommendation": [],
    }
    assert client.get("/api/admin/evaluations/audits").json() == []
