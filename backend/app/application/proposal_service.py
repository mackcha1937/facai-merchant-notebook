"""Agent 建议（Proposal）预览与取消用例。"""
import json

from sqlalchemy.orm import Session

from app.application import serializers
from app.domain.errors import NotFoundError
from app.repositories import proposals as proposal_repo


def get_proposal(db: Session, proposal_id: int) -> dict:
    proposal = proposal_repo.get_proposal(db, proposal_id)
    if proposal is None:
        raise NotFoundError("解析记录不存在")
    try:
        parsed = json.loads(proposal.parsed_json)
    except (json.JSONDecodeError, TypeError):
        parsed = {}
    return {
        "id": proposal.id,
        "status": proposal.status,
        "write_allowed": False,
        "prompt_version": proposal.prompt_version,
        "original_input": proposal.original_input,
        "created_at": proposal.created_at,
        **parsed,
    }


def cancel_proposal(db: Session, proposal_id: int) -> dict:
    proposal = proposal_repo.get_proposal(db, proposal_id)
    if proposal is None:
        raise NotFoundError("解析记录不存在")
    proposal_repo.set_status(db, proposal, "cancelled")
    serializers.save(db)
    return {"id": proposal.id, "status": "cancelled"}
