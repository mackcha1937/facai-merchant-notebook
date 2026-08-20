"""Agent 建议（Proposal）数据访问。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.models import AgentProposal


def create_proposal(
    db: Session,
    original_input: str,
    parsed_json: str,
    prompt_version: int | None,
    status: str = "pending",
) -> AgentProposal:
    proposal = AgentProposal(
        original_input=original_input,
        parsed_json=parsed_json,
        prompt_version=prompt_version,
        status=status,
    )
    db.add(proposal)
    db.flush()
    return proposal


def get_proposal(db: Session, proposal_id: int) -> AgentProposal | None:
    return db.scalar(select(AgentProposal).where(AgentProposal.id == proposal_id))


def set_status(db: Session, proposal: AgentProposal, status: str) -> None:
    proposal.status = status
    db.flush()


def mark_confirmed(db: Session, proposal: AgentProposal) -> None:
    """标记建议为已确认，并记录确认时间（幂等：只能从 pending 确认一次）。"""
    from datetime import datetime, timezone

    proposal.status = "confirmed"
    proposal.confirmed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.flush()
