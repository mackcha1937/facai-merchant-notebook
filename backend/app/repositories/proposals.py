"""Agent 建议（Proposal）数据访问（强制 tenant 过滤）。"""
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.tenant import get_current_tenant_id
from app.infrastructure.models import AgentProposal


def create_proposal(
    db: Session,
    original_input: str,
    parsed_json: str,
    prompt_version: int | None,
    status: str = "pending",
    **fields,
) -> AgentProposal:
    proposal = AgentProposal(
        tenant_id=get_current_tenant_id(),
        original_input=original_input,
        parsed_json=parsed_json,
        prompt_version=prompt_version,
        status=status,
        **fields,
    )
    db.add(proposal)
    db.flush()
    return proposal


def get_proposal(db: Session, proposal_id: int) -> AgentProposal | None:
    return db.scalar(
        select(AgentProposal).where(
            AgentProposal.id == proposal_id,
            AgentProposal.tenant_id == get_current_tenant_id(),
        )
    )


def get_by_idempotency_key(db: Session, idempotency_key: str) -> AgentProposal | None:
    return db.scalar(
        select(AgentProposal).where(
            AgentProposal.tenant_id == get_current_tenant_id(),
            AgentProposal.idempotency_key == idempotency_key,
        )
    )


def get_by_confirmation_idempotency_key(
    db: Session, idempotency_key: str
) -> AgentProposal | None:
    return db.scalar(
        select(AgentProposal).where(
            AgentProposal.tenant_id == get_current_tenant_id(),
            AgentProposal.confirmation_idempotency_key == idempotency_key,
        )
    )


def get_by_request_id(db: Session, request_id: str) -> AgentProposal | None:
    return db.scalar(
        select(AgentProposal).where(
            AgentProposal.tenant_id == get_current_tenant_id(),
            AgentProposal.request_id == request_id,
        )
    )


def claim_pending(
    db: Session,
    proposal_id: int,
    data_version: int,
    confirmation_idempotency_key: str,
    device_id: str,
    updated_at: datetime,
) -> bool:
    result = db.execute(
        update(AgentProposal)
        .where(
            AgentProposal.id == proposal_id,
            AgentProposal.tenant_id == get_current_tenant_id(),
            AgentProposal.status == "pending",
            AgentProposal.data_version == data_version,
        )
        .values(
            status="processing",
            confirmation_idempotency_key=confirmation_idempotency_key,
            confirmed_by_device=device_id,
            updated_at=updated_at,
        )
    )
    return result.rowcount == 1


def set_status(db: Session, proposal: AgentProposal, status: str) -> None:
    if proposal.tenant_id != get_current_tenant_id():
        from app.domain.errors import DomainError

        raise DomainError("跨租户操作被拒绝")
    proposal.status = status
    db.flush()


def mark_confirmed(db: Session, proposal: AgentProposal) -> None:
    """标记建议为已确认，并记录确认时间（幂等：只能从 pending 确认一次）。"""
    if proposal.tenant_id != get_current_tenant_id():
        from app.domain.errors import DomainError

        raise DomainError("跨租户操作被拒绝")
    proposal.status = "confirmed"
    proposal.confirmed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.flush()
