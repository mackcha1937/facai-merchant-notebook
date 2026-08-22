"""阶段3会话仓储；所有查询在 SQL 层强制 tenant/owner 边界。"""
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.tenant import get_current_tenant_id
from app.infrastructure.models import (
    ContextSummary,
    ConversationSession,
    ConversationThread,
    EntityMention,
    Message,
    MessageBlock,
    PendingAction,
)


def get_thread(db: Session, owner_id: int) -> ConversationThread | None:
    return db.scalar(
        select(ConversationThread).where(
            ConversationThread.tenant_id == get_current_tenant_id(),
            ConversationThread.owner_id == owner_id,
        )
    )


def get_thread_by_id(db: Session, thread_id: int, owner_id: int) -> ConversationThread | None:
    return db.scalar(
        select(ConversationThread).where(
            ConversationThread.id == thread_id,
            ConversationThread.tenant_id == get_current_tenant_id(),
            ConversationThread.owner_id == owner_id,
        )
    )


def get_session(db: Session, thread_id: int, session_date: str) -> ConversationSession | None:
    return db.scalar(
        select(ConversationSession).where(
            ConversationSession.tenant_id == get_current_tenant_id(),
            ConversationSession.thread_id == thread_id,
            ConversationSession.session_date == session_date,
        )
    )


def list_messages(
    db: Session, thread_id: int, *, before: int | None = None, limit: int = 30
) -> list[tuple[Message, ConversationSession]]:
    stmt = (
        select(Message, ConversationSession)
        .join(ConversationSession, ConversationSession.id == Message.session_id)
        .where(
            Message.tenant_id == get_current_tenant_id(),
            ConversationSession.tenant_id == get_current_tenant_id(),
            ConversationSession.thread_id == thread_id,
        )
    )
    if before is not None:
        stmt = stmt.where(Message.id < before)
    return list(db.execute(stmt.order_by(Message.id.desc()).limit(limit)).all())


def list_blocks(db: Session, message_ids: list[int]) -> dict[int, list[MessageBlock]]:
    if not message_ids:
        return {}
    rows = db.scalars(
        select(MessageBlock)
        .where(
            MessageBlock.tenant_id == get_current_tenant_id(),
            MessageBlock.message_id.in_(message_ids),
        )
        .order_by(MessageBlock.id)
    ).all()
    result: dict[int, list[MessageBlock]] = {}
    for row in rows:
        result.setdefault(row.message_id, []).append(row)
    return result


def get_message_by_request(db: Session, request_id: str) -> Message | None:
    return db.scalar(
        select(Message).where(
            Message.tenant_id == get_current_tenant_id(), Message.request_id == request_id
        )
    )


def get_block_for_proposal(db: Session, proposal_id: int) -> MessageBlock | None:
    return db.scalar(
        select(MessageBlock).where(
            MessageBlock.tenant_id == get_current_tenant_id(),
            MessageBlock.proposal_id == proposal_id,
            MessageBlock.block_type == "confirm_card",
        ).order_by(MessageBlock.id.desc())
    )


def get_pending_for_proposal(db: Session, proposal_id: int) -> PendingAction | None:
    return db.scalar(
        select(PendingAction).where(
            PendingAction.tenant_id == get_current_tenant_id(),
            PendingAction.proposal_id == proposal_id,
        )
    )


def list_pending(db: Session, thread_id: int) -> list[PendingAction]:
    return list(
        db.scalars(
            select(PendingAction).where(
                PendingAction.tenant_id == get_current_tenant_id(),
                PendingAction.thread_id == thread_id,
                PendingAction.status.in_(("pending", "stale", "expired")),
            ).order_by(PendingAction.created_at.desc())
        ).all()
    )


def get_summary(db: Session, session_id: int) -> ContextSummary | None:
    return db.scalar(
        select(ContextSummary).where(
            ContextSummary.tenant_id == get_current_tenant_id(),
            ContextSummary.session_id == session_id,
        )
    )


def get_latest_summary(db: Session, thread_id: int) -> ContextSummary | None:
    return db.scalar(
        select(ContextSummary)
        .join(ConversationSession, ConversationSession.id == ContextSummary.session_id)
        .where(
            ContextSummary.tenant_id == get_current_tenant_id(),
            ConversationSession.tenant_id == get_current_tenant_id(),
            ConversationSession.thread_id == thread_id,
        )
        .order_by(ContextSummary.generated_at.desc(), ContextSummary.id.desc())
        .limit(1)
    )


def recent_relevant_messages(
    db: Session, thread_id: int, terms: list[str], limit: int = 12
) -> list[Message]:
    stmt = (
        select(Message)
        .join(ConversationSession, ConversationSession.id == Message.session_id)
        .where(
            Message.tenant_id == get_current_tenant_id(),
            ConversationSession.tenant_id == get_current_tenant_id(),
            ConversationSession.thread_id == thread_id,
        )
    )
    cleaned = [term.strip() for term in terms if term and term.strip()]
    if cleaned:
        stmt = stmt.where(or_(*(Message.content.contains(term) for term in cleaned)))
    return list(db.scalars(stmt.order_by(Message.id.desc()).limit(limit)).all())
