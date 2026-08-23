"""阶段3店主会话、Proposal 与验证状态 API。"""
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.application import conversation_service, customer_read_service, stage3_proposal_service
from app.core.database import get_db
from app.core.rbac import require_owner
from app.core.tenant import get_current_tenant_id
from app.domain.errors import NotFoundError
from app.infrastructure.models import (
    CustomerFact, LedgerEntry, Message, ConversationSession, PendingAction, Product,
)
from app.schemas.conversation import (
    ChatTurnRequest,
    ProposalCancelRequest,
    ProposalConfirmRequest,
    ProposalEditRequest,
    ProposalRegenerateRequest,
)

router = APIRouter(prefix="/api", tags=["v2-stage3"])


@router.get("/owner/chat/thread")
def get_thread(db: Session = Depends(get_db)):
    require_owner()
    return conversation_service.get_main_thread(db)


@router.get("/owner/chat/history")
def get_history(
    before: int | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    require_owner()
    return conversation_service.history(db, before=before, limit=limit)


@router.get("/owner/chat/pending")
def get_pending(db: Session = Depends(get_db)):
    require_owner()
    return conversation_service.pending_actions(db)


@router.post("/owner/chat/turn")
def chat_turn(data: ChatTurnRequest, db: Session = Depends(get_db)):
    require_owner()
    return conversation_service.chat_turn(db, data)


@router.post("/owner/chat/turn/stream")
def chat_turn_stream(data: ChatTurnRequest, db: Session = Depends(get_db)):
    """受控阶段3流：先完成持久化，再发送 text_delta 与 validated_block。"""
    require_owner()
    result = conversation_service.chat_turn(db, data)

    def events():
        text_payload = json.dumps(
            {"text": result.get("message") or ("已生成统一确认卡" if result.get("proposal") else "已处理")},
            ensure_ascii=False,
        )
        block_payload = json.dumps(result, ensure_ascii=False)
        yield f"event: text_delta\ndata: {text_payload}\n\n"
        yield f"event: validated_block\ndata: {block_payload}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/owner/chat/context")
def chat_context(data: dict, db: Session = Depends(get_db)):
    require_owner()
    return conversation_service.assemble_context(db, str(data.get("text") or ""))


@router.post("/owner/messages/{message_id}/read")
def mark_message_read(message_id: int, db: Session = Depends(get_db)):
    require_owner()
    thread = conversation_service.get_or_create_thread(db)
    message = db.scalar(
        select(Message)
        .join(ConversationSession, ConversationSession.id == Message.session_id)
        .where(
            Message.id == message_id,
            Message.tenant_id == get_current_tenant_id(),
            ConversationSession.tenant_id == get_current_tenant_id(),
            ConversationSession.thread_id == thread.id,
        )
    )
    if message is None:
        raise NotFoundError("消息不存在")
    if message.read_at is None:
        message.read_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
    return {"id": message.id, "read_at": message.read_at}


@router.post("/owner/pending/{pending_id}/read")
def mark_pending_read(pending_id: int, db: Session = Depends(get_db)):
    require_owner()
    thread = conversation_service.get_or_create_thread(db)
    pending = db.scalar(
        select(PendingAction).where(
            PendingAction.id == pending_id,
            PendingAction.tenant_id == get_current_tenant_id(),
            PendingAction.thread_id == thread.id,
        )
    )
    if pending is None:
        raise NotFoundError("待办不存在")
    if pending.read_at is None:
        pending.read_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
    return {"id": pending.id, "read_at": pending.read_at}


@router.post("/owner/proposals/{proposal_id}/confirm")
def confirm_proposal(
    proposal_id: int, data: ProposalConfirmRequest, db: Session = Depends(get_db)
):
    require_owner()
    return stage3_proposal_service.confirm(db, proposal_id, data)


@router.post("/owner/proposals/{proposal_id}/cancel")
def cancel_proposal(
    proposal_id: int, data: ProposalCancelRequest, db: Session = Depends(get_db)
):
    require_owner()
    return stage3_proposal_service.cancel(db, proposal_id, data)


@router.post("/owner/proposals/{proposal_id}/edit")
def edit_proposal(
    proposal_id: int, data: ProposalEditRequest, db: Session = Depends(get_db)
):
    require_owner()
    return stage3_proposal_service.edit(db, proposal_id, data)


@router.post("/owner/proposals/{proposal_id}/regenerate")
def regenerate_proposal(
    proposal_id: int, data: ProposalRegenerateRequest, db: Session = Depends(get_db)
):
    require_owner()
    return stage3_proposal_service.regenerate(db, proposal_id, data)


@router.get("/owner/customers/{customer_id}/record")
def get_current_customer_record(customer_id: int, db: Session = Depends(get_db)):
    require_owner()
    result = customer_read_service.get_customer_overview(db, customer_id)
    last_ledger_id = db.scalar(
        select(func.coalesce(func.max(LedgerEntry.id), 0)).where(
            LedgerEntry.tenant_id == get_current_tenant_id(),
            LedgerEntry.customer_id == customer_id,
        )
    ) or 0
    last_fact_id = db.scalar(
        select(func.coalesce(func.max(CustomerFact.id), 0)).where(
            CustomerFact.tenant_id == get_current_tenant_id(),
            CustomerFact.customer_id == customer_id,
        )
    ) or 0
    max_product_version = db.scalar(
        select(func.coalesce(func.max(Product.version), 0))
        .join(LedgerEntry, LedgerEntry.product_id == Product.id)
        .where(
            LedgerEntry.tenant_id == get_current_tenant_id(),
            LedgerEntry.customer_id == customer_id,
            Product.tenant_id == get_current_tenant_id(),
        )
    ) or 0
    result["data_version"] = int(last_ledger_id) * 1_000_000 + int(last_fact_id) * 1_000 + int(max_product_version)
    result["authoritative"] = True
    return result


@router.get("/v2-stage3/status")
def stage3_status(db: Session = Depends(get_db)):
    require_owner()
    migration = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    counts = {}
    for table in ("conversation_threads", "conversation_sessions", "messages", "pending_actions", "agent_proposals"):
        counts[table] = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
    root = Path(__file__).resolve().parents[4]
    report_path = root / "v2.0" / "stage-3-delivery" / "test-results.json"
    test_results = {"status": "未验证"}
    if report_path.exists():
        try:
            test_results = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            test_results = {"status": "未验证", "detail": "测试报告暂不可读"}
    return {
        "stage": 3,
        "migration": migration,
        "timezone": "Asia/Shanghai",
        "counts": counts,
        "capabilities": {
            "single_main_thread": True,
            "daily_sessions": True,
            "cursor_history": True,
            "pending_recovery": True,
            "absolute_relative_dates": True,
            "unified_proposal": True,
            "transactional_batch": True,
            "strong_idempotency": True,
            "cross_device_conflict": True,
            "latest_authoritative_cards": True,
            "external_paid_model_used_in_tests": False,
        },
        "test_results": test_results,
    }
