"""阶段5知识 Proposal、管理员发布管理与只读 RAG 证据 API。"""
import json
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.application import knowledge_service, rag_service, stage3_proposal_service
from app.core.database import get_db
from app.core.rbac import require_admin, require_owner
from app.infrastructure.models import EmbeddingRecord, KnowledgeChunk, KnowledgeDocument
from app.schemas.conversation import (
    KnowledgeProposalRequest, KnowledgeRetrieveRequest, KnowledgeWithdrawRequest,
    ProposalConfirmRequest,
)


router = APIRouter(prefix="/api", tags=["v2-stage5"])


@router.get("/owner/knowledge/status")
def owner_knowledge_status(db: Session = Depends(get_db)):
    require_owner()
    return knowledge_service.owner_status(db)


@router.get("/owner/knowledge")
def owner_knowledge(db: Session = Depends(get_db)):
    require_owner()
    return knowledge_service.list_owner_knowledge(db)


@router.post("/owner/knowledge/retrieve")
def owner_retrieve(data: KnowledgeRetrieveRequest, db: Session = Depends(get_db)):
    require_owner()
    return rag_service.retrieve(db, data)


@router.get("/admin/knowledge")
def admin_list_knowledge(db: Session = Depends(get_db)):
    require_admin()
    return knowledge_service.list_knowledge(db, include_history=True)


@router.post("/admin/knowledge/proposals")
def admin_create_knowledge_proposal(data: KnowledgeProposalRequest, db: Session = Depends(get_db)):
    require_admin()
    return knowledge_service.create_knowledge_proposal(db, data)


@router.post("/admin/knowledge/withdraw-proposals")
def admin_withdraw_knowledge(data: KnowledgeWithdrawRequest, db: Session = Depends(get_db)):
    require_admin()
    return knowledge_service.create_withdraw_proposal(db, data)


@router.post("/admin/knowledge/proposals/{proposal_id}/confirm")
def admin_confirm_knowledge(
    proposal_id: int, data: ProposalConfirmRequest, db: Session = Depends(get_db)
):
    require_admin()
    return stage3_proposal_service.confirm(db, proposal_id, data)


@router.post("/admin/knowledge/{entity_type}/{entity_id}/reindex")
def admin_reindex(entity_type: str, entity_id: int, db: Session = Depends(get_db)):
    require_admin()
    return knowledge_service.reindex_current(db, entity_type, entity_id)


@router.get("/v2-stage5/status")
def stage5_status(db: Session = Depends(get_db)):
    require_owner()
    try:
        migration = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    except OperationalError:
        migration = "metadata-test-db"
    counts = {
        "knowledge_documents": db.scalar(select(func.count(KnowledgeDocument.id))) or 0,
        "active_documents": db.scalar(select(func.count(KnowledgeDocument.id)).where(
            KnowledgeDocument.confirmed.is_(True), KnowledgeDocument.active.is_(True),
        )) or 0,
        "knowledge_chunks": db.scalar(select(func.count(KnowledgeChunk.id))) or 0,
        "embedding_records": db.scalar(select(func.count(EmbeddingRecord.id))) or 0,
    }
    root = Path(__file__).resolve().parents[4]
    report_path = root / "v2.0" / "stage-5-delivery" / "test-results.json"
    results = {"status": "未验证"}
    if report_path.exists():
        try:
            results = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            results = {"status": "未验证", "detail": "测试报告暂不可读"}
    return {
        "stage": 5, "migration": migration, "counts": counts,
        "capabilities": {
            "proposal_confirmation_only": True,
            "knowledge_versioning": True,
            "confirmed_current_active_filter": True,
            "local_deterministic_embedding": True,
            "embedding_checksum_idempotency": True,
            "dimension_isolation": True,
            "hybrid_retrieval": True,
            "tenant_metadata_filter": True,
            "pii_injection_script_gate": True,
            "stable_evidence_only": True,
            "recommendation_built": False,
            "external_embedding_used": False,
            "real_chat_model_required": False,
        },
        "runtime": {
            "embedding_provider": "facai-local",
            "embedding_model": "char-ngram-sha256-v1",
            "dimension": 32,
            "network_required": False,
            "deepseek_called_in_stage5": False,
        },
        "owner_status": knowledge_service.owner_status(db),
        "test_results": results,
    }
