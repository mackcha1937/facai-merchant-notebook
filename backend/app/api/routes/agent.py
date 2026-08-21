"""Agent 解析与模糊搜索路由（业务操作需 owner）。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agent import agent_service, matching
from app.application import confirmation_service, proposal_service
from app.core.database import get_db
from app.core.rbac import require_owner
from app.repositories import customers as customer_repo
from app.schemas.agent import ConfirmRequest, FuzzySearchRequest, InterpretRequest, PrecheckRequest

router = APIRouter(prefix="/api", tags=["agent"])


@router.post("/agent/interpret")
def interpret(data: InterpretRequest, db: Session = Depends(get_db)):
    require_owner()
    return agent_service.interpret(db, data.text)


@router.get("/agent/proposals/{proposal_id}")
def get_proposal(proposal_id: int, db: Session = Depends(get_db)):
    require_owner()
    return proposal_service.get_proposal(db, proposal_id)


@router.post("/agent/proposals/{proposal_id}/cancel")
def cancel_proposal(proposal_id: int, db: Session = Depends(get_db)):
    require_owner()
    return proposal_service.cancel_proposal(db, proposal_id)


@router.post("/agent/proposals/{proposal_id}/precheck")
def precheck_proposal(proposal_id: int, data: PrecheckRequest, db: Session = Depends(get_db)):
    require_owner()
    return confirmation_service.precheck(db, proposal_id, data)


@router.post("/agent/proposals/{proposal_id}/confirm")
def confirm_proposal(proposal_id: int, data: ConfirmRequest, db: Session = Depends(get_db)):
    require_owner()
    return confirmation_service.confirm(db, proposal_id, data)


@router.post("/customers/search-fuzzy")
def search_fuzzy(data: FuzzySearchRequest, db: Session = Depends(get_db)):
    require_owner()
    customers = customer_repo.list_customers(db)
    customer_dicts = [
        {
            "id": c.id,
            "display_name": c.display_name,
            "aliases": [a.alias for a in c.aliases if a.deleted_at is None],
        }
        for c in customers
    ]
    candidates = matching.match_customers(data.query, customer_dicts, limit=3)
    return {"query": data.query, "candidates": candidates}
