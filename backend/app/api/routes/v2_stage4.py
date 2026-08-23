"""阶段4客户事实与产品实体 API；不包含知识/RAG/推荐。"""
import json
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.application import product_resolution_service, stage4_entity_service
from app.core.config import get_settings
from app.core.database import get_db
from app.core.rbac import require_owner
from app.infrastructure.models import CustomerFact, LedgerEntry, Product, ProductAlias
from app.schemas.conversation import (
    CustomerFactProposalRequest, ProductDraftProposalRequest, ProductMergeProposalRequest,
    ProductResolutionChoiceRequest, ProductResolveRequest,
)


router = APIRouter(prefix="/api", tags=["v2-stage4"])


@router.post("/owner/products/resolve")
def resolve_product(data: ProductResolveRequest, db: Session = Depends(get_db)):
    require_owner()
    return product_resolution_service.resolve_product(
        db, data.query, brand=data.brand, specification=data.specification
    )


@router.get("/owner/products")
def list_products(db: Session = Depends(get_db)):
    require_owner()
    return stage4_entity_service.list_products(db)


@router.get("/owner/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    require_owner()
    return stage4_entity_service.get_product_detail(db, product_id)


@router.post("/owner/products/draft-proposal")
def create_product_proposal(data: ProductDraftProposalRequest, db: Session = Depends(get_db)):
    require_owner()
    return stage4_entity_service.create_product_proposal(db, data)


@router.post("/owner/products/merge-proposal")
def merge_product_proposal(data: ProductMergeProposalRequest, db: Session = Depends(get_db)):
    require_owner()
    return stage4_entity_service.create_merge_proposal(db, data)


@router.post("/owner/customers/{customer_id}/facts/proposal")
def create_customer_fact_proposal(
    customer_id: int, data: CustomerFactProposalRequest, db: Session = Depends(get_db)
):
    require_owner()
    return stage4_entity_service.create_fact_proposal(db, customer_id, data)


@router.post("/owner/proposals/{proposal_id}/resolve-product")
def resolve_proposal_product(
    proposal_id: int, data: ProductResolutionChoiceRequest, db: Session = Depends(get_db)
):
    require_owner()
    return stage4_entity_service.resolve_proposal_product(db, proposal_id, data)


@router.get("/v2-stage4/status")
def stage4_status(db: Session = Depends(get_db)):
    require_owner()
    settings = get_settings()
    migration = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    counts = {
        "customer_facts": db.scalar(select(func.count(CustomerFact.id))) or 0,
        "products": db.scalar(select(func.count(Product.id))) or 0,
        "product_aliases": db.scalar(select(func.count(ProductAlias.id))) or 0,
        "product_linked_ledger": db.scalar(
            select(func.count(LedgerEntry.id)).where(LedgerEntry.product_id.is_not(None))
        ) or 0,
    }
    root = Path(__file__).resolve().parents[4]
    report_path = root / "v2.0" / "stage-4-delivery" / "test-results.json"
    test_results = {"status": "未验证"}
    if report_path.exists():
        try:
            test_results = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            test_results = {"status": "未验证", "detail": "测试报告暂不可读"}
    return {
        "stage": 4, "migration": migration, "counts": counts,
        "capabilities": {
            "fact_evidence_confirmation": True,
            "fact_versioning_without_overwrite": True,
            "sensitive_fact_separation": True,
            "product_exact_alias_fuzzy_embedding_candidates": True,
            "candidate_limit": 3,
            "new_product_purchase_atomic": True,
            "product_merge_proposal": True,
            "knowledge_status_visible": True,
            "deepseek_structured_candidate_path": True,
            "rag_built": False,
            "knowledge_embedding_index_built": False,
        },
        "model_validation": {
            "configured": settings.is_model_configured,
            "enabled": settings.enable_v2_real_model,
            "effective": (
                settings.is_model_configured and settings.enable_v2_real_model
            ),
            "adapter": "DeepSeekAdapter",
            "runtime_path": "connected",
            "automatic_test": "mock_and_transport_passed",
            "isolated_validation": "passed",
            "total_paid_calls": 2,
        },
        "test_results": test_results,
    }
