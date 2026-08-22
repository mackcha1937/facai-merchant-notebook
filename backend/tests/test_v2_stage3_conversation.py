"""阶段3真实业务测试：日期、恢复、事务、幂等、冲突、租户与上下文。"""
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.application import conversation_service, stage3_proposal_service
from app.application.relative_dates import resolve_relative_date
from app.application.stage3_authority import build_authority_snapshot, canonical_json
from app.core.tenant import set_current_owner_id, set_current_tenant_id
from app.domain.errors import ConflictError, DomainError, NotFoundError
from app.infrastructure.models import (
    AgentProposal,
    Base,
    ConversationSession,
    ConversationThread,
    LedgerEntry,
    Message,
    PendingAction,
)
from app.repositories import customers as customer_repo
from app.repositories import packages as package_repo
from app.repositories import services as service_repo
from app.schemas.conversation import (
    ChatTurnRequest,
    ProposalCancelRequest,
    ProposalConfirmRequest,
    ProposalRegenerateRequest,
)


DAY1 = datetime(2026, 8, 22, 4, 0, tzinfo=timezone.utc)  # 上海 12:00
DAY2 = DAY1 + timedelta(days=1)


@pytest.fixture(autouse=True)
def reset_context():
    set_current_tenant_id(1)
    set_current_owner_id(1)
    yield
    set_current_tenant_id(None)
    set_current_owner_id(None)


def seed(db, second_service=False):
    customer = customer_repo.create_customer(db, "测试顾客甲", ["甲姐"])
    service = service_repo.create_service(db, "基础护理", "active")
    package_repo.create_package(db, customer.id, service.id, 5, 0, None, None)
    other = None
    if second_service:
        other = service_repo.create_service(db, "肩颈放松", "active")
        package_repo.create_package(db, customer.id, other.id, 6, 0, None, None)
    db.commit()
    return customer, service, other


def turn(db, text="测试顾客甲昨天基础护理1次", key="turn-key-0001", now=DAY1):
    request = ChatTurnRequest(
        text=text, request_id=f"request-{key}", idempotency_key=key, device_id="phone"
    )
    return conversation_service.chat_turn(db, request, now=now)


def confirm(db, proposal, key="confirm-key-0001", device="phone", now=DAY1):
    request = ProposalConfirmRequest(
        idempotency_key=key, device_id=device, data_version=proposal["data_version"]
    )
    return stage3_proposal_service.confirm(db, proposal["id"], request, now=now)


def ledger_count(db):
    return db.scalar(select(func.count(LedgerEntry.id))) or 0


def test_same_owner_gets_one_main_thread(db_session):
    first = conversation_service.get_main_thread(db_session, DAY1)
    second = conversation_service.get_main_thread(db_session, DAY1)
    assert first["id"] == second["id"]
    assert db_session.scalar(select(func.count(ConversationThread.id))) == 1


def test_same_day_session_and_cross_day_separator_source(db_session):
    seed(db_session)
    turn(db_session, key="turn-key-day-a", now=DAY1)
    turn(db_session, key="turn-key-day-b", now=DAY1 + timedelta(hours=2))
    turn(db_session, key="turn-key-day-c", now=DAY2)
    sessions = db_session.scalars(select(ConversationSession).order_by(ConversationSession.session_date)).all()
    assert [row.session_date for row in sessions] == ["2026-08-22", "2026-08-23"]
    history = conversation_service.history(db_session, limit=100)
    assert {m["session_date"] for m in history["messages"]} == {"2026-08-22", "2026-08-23"}


def test_cursor_history_returns_older_page_without_duplicates(db_session):
    seed(db_session)
    for index in range(5):
        turn(db_session, key=f"turn-key-page-{index}", now=DAY1)
    newest = conversation_service.history(db_session, limit=4)
    older = conversation_service.history(db_session, before=newest["next_cursor"], limit=20)
    newest_ids = {row["id"] for row in newest["messages"]}
    older_ids = {row["id"] for row in older["messages"]}
    assert newest["has_more"] is True
    assert newest_ids.isdisjoint(older_ids)


def test_relative_date_is_fixed_when_continued_next_day(db_session):
    seed(db_session)
    created = turn(db_session, now=DAY1)
    proposal = created["proposal"]
    assert proposal["absolute_date"] == "2026-08-21"
    pending = conversation_service.pending_actions(db_session, now=DAY2)["items"]
    restored = next(item for item in pending if item["proposal"]["id"] == proposal["id"])
    assert restored["proposal"]["absolute_date"] == "2026-08-21"


@pytest.mark.parametrize(
    ("text", "expected"),
    [("月底再处理", "2026-08-31"), ("三天后再处理", "2026-08-25"), ("明天处理", "2026-08-23")],
)
def test_relative_date_examples_use_shanghai_calendar(text, expected):
    assert resolve_relative_date(text, DAY1)["date"] == expected


def test_repeated_chat_request_does_not_duplicate_messages_or_proposal(db_session):
    seed(db_session)
    request = ChatTurnRequest(
        text="测试顾客甲昨天基础护理1次",
        request_id="request-repeat-chat",
        idempotency_key="turn-repeat-chat",
        device_id="web",
    )
    first = conversation_service.chat_turn(db_session, request, now=DAY1)
    second = conversation_service.chat_turn(db_session, request, now=DAY1)
    assert first["proposal"]["id"] == second["proposal"]["id"]
    assert second["idempotent_replay"] is True
    assert db_session.scalar(select(func.count(AgentProposal.id))) == 1
    assert db_session.scalar(select(func.count(Message.id))) == 2


def test_clarification_request_retry_is_idempotent(db_session):
    seed(db_session)
    request = ChatTurnRequest(
        text="这条信息暂时无法解析", request_id="request-clarify-repeat",
        idempotency_key="clarify-repeat-key", device_id="phone",
    )
    first = conversation_service.chat_turn(db_session, request, now=DAY1)
    second = conversation_service.chat_turn(db_session, request, now=DAY1)
    assert first["status"] == second["status"] == "needs_clarification"
    assert second["idempotent_replay"] is True
    assert db_session.scalar(select(func.count(Message.id))) == 2


def test_pending_cancel_expire_and_regenerate_preserves_absolute_date(db_session):
    seed(db_session)
    cancelled = turn(db_session, key="turn-key-cancel", now=DAY1)["proposal"]
    result = stage3_proposal_service.cancel(
        db_session, cancelled["id"],
        ProposalCancelRequest(idempotency_key="cancel-key-0001", device_id="web"), now=DAY1,
    )
    assert result["status"] == "cancelled"
    assert ledger_count(db_session) == 0

    expired = turn(db_session, key="turn-key-expire", now=DAY1)["proposal"]
    items = conversation_service.pending_actions(db_session, now=DAY2 + timedelta(days=1))["items"]
    assert next(i for i in items if i["proposal"]["id"] == expired["id"])["status"] == "expired"
    regenerated = stage3_proposal_service.regenerate(
        db_session, expired["id"],
        ProposalRegenerateRequest(
            request_id="request-regenerated-01", idempotency_key="regenerated-key-01", device_id="web"
        ), now=DAY2 + timedelta(days=1),
    )["proposal"]
    assert regenerated["status"] == "pending"
    assert regenerated["absolute_date"] == expired["absolute_date"]


def test_single_proposal_confirm_and_idempotent_retry(db_session):
    seed(db_session)
    proposal = turn(db_session)["proposal"]
    first = confirm(db_session, proposal)
    second = confirm(db_session, proposal)
    assert first["status"] == "confirmed"
    assert second["idempotent_replay"] is True
    assert ledger_count(db_session) == 1


def test_multi_action_success_is_one_proposal(db_session):
    seed(db_session, second_service=True)
    result = turn(
        db_session,
        text="测试顾客甲今天基础护理1次，肩颈放松2次",
        key="turn-key-multi-ok",
    )
    assert len(result["proposal"]["actions"]) == 2
    confirmed = confirm(db_session, result["proposal"], key="confirm-key-multi-ok")
    assert len(confirmed["results"]) == 2
    assert ledger_count(db_session) == 2


def test_multi_action_runtime_failure_rolls_back_whole_group(db_session):
    seed(db_session)
    proposal_data = turn(db_session, key="turn-key-multi-rollback")["proposal"]
    proposal = db_session.get(AgentProposal, proposal_data["id"])
    parsed = json.loads(proposal.parsed_json)
    parsed["actions"][0]["quantity"] = 3
    parsed["actions"].append(dict(parsed["actions"][0]))
    proposal.parsed_json = json.dumps(parsed, ensure_ascii=False)
    proposal.authority_snapshot_json = canonical_json(build_authority_snapshot(db_session, parsed))
    db_session.commit()

    with pytest.raises(DomainError):
        confirm(db_session, proposal_data, key="confirm-key-rollback")
    assert ledger_count(db_session) == 0
    db_session.refresh(proposal)
    assert proposal.status == "pending"


def test_other_device_receives_recoverable_conflict(db_session):
    seed(db_session)
    proposal = turn(db_session, key="turn-key-devices")["proposal"]
    confirm(db_session, proposal, key="confirm-device-phone", device="phone")
    with pytest.raises(ConflictError) as error:
        confirm(db_session, proposal, key="confirm-device-web", device="web")
    assert error.value.payload["conflict_type"] == "already_confirmed"
    assert error.value.payload["original_result"]["status"] == "confirmed"
    assert ledger_count(db_session) == 1


def test_phone_and_web_true_concurrent_confirm_only_one_writes(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'concurrent.db'}",
        connect_args={"check_same_thread": False, "timeout": 3},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    setup = factory()
    seed(setup)
    proposal = turn(setup, key="turn-key-true-concurrent")["proposal"]
    setup.close()
    barrier = threading.Barrier(2)

    def worker(device):
        session = factory()
        request = ProposalConfirmRequest(
            idempotency_key=f"confirm-concurrent-{device}", device_id=device,
            data_version=proposal["data_version"],
        )
        barrier.wait()
        try:
            result = stage3_proposal_service.confirm(session, proposal["id"], request, now=DAY1)
            return result["status"]
        except ConflictError as exc:
            return exc.payload["status"]
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(worker, ("phone", "web")))
    verify = factory()
    assert sorted(outcomes) == ["confirmed", "conflict"]
    assert ledger_count(verify) == 1
    verify.close()
    engine.dispose()


def test_authority_change_marks_proposal_stale_with_diff(db_session):
    customer, service, _ = seed(db_session)
    package = package_repo.list_packages_for_customer_service(db_session, customer.id, service.id)[0]
    proposal = turn(db_session, key="turn-key-stale")["proposal"]
    from app.repositories import ledger as ledger_repo

    ledger_repo.create_ledger_entry(
        db_session, customer.id, "package_consumption", service.id, None, 1, None,
        "2026-08-22", package_id=package.id,
    )
    db_session.commit()
    with pytest.raises(ConflictError) as error:
        confirm(db_session, proposal, key="confirm-key-stale")
    assert error.value.payload["status"] == "stale"
    assert error.value.payload["differences"]
    assert ledger_count(db_session) == 1  # 只有外部变化，没有执行旧 Proposal


def test_context_is_budgeted_and_not_full_history(db_session):
    seed(db_session)
    for index in range(15):
        turn(db_session, key=f"turn-key-context-{index}")
    context = conversation_service.assemble_context(db_session, "测试顾客甲基础护理")
    assert context["full_history_sent"] is False
    assert len(context["recent_relevant_messages"]) <= 12
    assert context["pending_actions"]
    assert context["summary"]["entity_ids"]
    assert context["latest_authoritative_objects"]


def test_model_parse_failure_produces_no_proposal_or_ledger(db_session, monkeypatch):
    seed(db_session)

    def fail(*_args, **_kwargs):
        raise DomainError("受控模型不可用")

    monkeypatch.setattr(conversation_service, "_controlled_parse", fail)
    request = ChatTurnRequest(
        text="测试顾客甲基础护理1次", request_id="request-model-fail", idempotency_key="turn-model-fail"
    )
    with pytest.raises(DomainError):
        conversation_service.chat_turn(db_session, request, now=DAY1)
    assert db_session.scalar(select(func.count(AgentProposal.id))) == 0
    assert ledger_count(db_session) == 0


def test_cross_tenant_thread_message_and_proposal_are_hidden(db_session):
    seed(db_session)
    proposal = turn(db_session, key="turn-key-tenant")["proposal"]
    thread_id = conversation_service.get_main_thread(db_session, DAY1)["id"]
    set_current_tenant_id(2)
    set_current_owner_id(2)
    assert conversation_service.get_or_create_thread(db_session).id != thread_id
    with pytest.raises(NotFoundError):
        stage3_proposal_service.confirm(
            db_session, proposal["id"],
            ProposalConfirmRequest(
                idempotency_key="confirm-cross-tenant", device_id="web", data_version=proposal["data_version"]
            ), now=DAY1,
        )


def test_latest_customer_record_reads_authoritative_balance(client, db_session):
    customer, _, _ = seed(db_session)
    before = client.get(f"/api/owner/customers/{customer.id}/record").json()
    proposal = turn(db_session, key="turn-key-latest-card")["proposal"]
    confirm(db_session, proposal, key="confirm-key-latest-card")
    after = client.get(f"/api/owner/customers/{customer.id}/record").json()
    assert before["services"][0]["total_remaining_count"] == 5
    assert after["services"][0]["total_remaining_count"] == 4
    assert after["authoritative"] is True
    assert after["data_version"] > before["data_version"]


def test_api_conflict_is_http_409_and_recoverable(client, db_session):
    seed(db_session)
    proposal = turn(db_session, key="turn-key-api-conflict")["proposal"]
    body = {"idempotency_key": "confirm-api-phone", "device_id": "phone", "data_version": 1}
    assert client.post(f"/api/owner/proposals/{proposal['id']}/confirm", json=body).status_code == 200
    body["idempotency_key"] = "confirm-api-web"
    body["device_id"] = "web"
    response = client.post(f"/api/owner/proposals/{proposal['id']}/confirm", json=body)
    assert response.status_code == 409
    assert response.json()["recoverable"] is True


def test_chat_sse_emits_text_then_validated_block_without_duplicate_proposal(client, db_session):
    seed(db_session)
    body = {
        "text": "测试顾客甲昨天基础护理1次",
        "request_id": "request-sse-stage3",
        "idempotency_key": "idempotency-sse-stage3",
        "device_id": "web",
    }
    response = client.post("/api/owner/chat/turn/stream", json=body)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: text_delta" in response.text
    assert "event: validated_block" in response.text
    retry = client.post("/api/owner/chat/turn/stream", json=body)
    assert "\"idempotent_replay\": true" in retry.text
    assert db_session.scalar(select(func.count(AgentProposal.id))) == 1
