"""阶段5安全混合检索：实体当前知识 > 关键词/别名 > 本地向量。"""
import json
import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.knowledge_security import safe_for_embedding_query
from app.application.knowledge_service import build_embedding_adapter, build_vector_store
from app.application.product_resolution_service import normalize_product_text
from app.core.tenant import get_current_tenant_id
from app.domain.errors import DomainError
from app.infrastructure.embedding import EmbeddingError
from app.infrastructure.models import (
    EmbeddingRecord, KnowledgeDocument, Product, ProductAlias, Service,
)


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise EmbeddingError("dimension_mismatch")
    denominator = math.sqrt(sum(v * v for v in left)) * math.sqrt(sum(v * v for v in right))
    return sum(a * b for a, b in zip(left, right)) / denominator if denominator else 0.0


def _snippet(text: str, query: str, limit: int = 240) -> str:
    clean = " ".join(text.split())
    location = clean.lower().find(query.lower())
    start = max(0, location - 50) if location >= 0 else 0
    value = clean[start:start + limit]
    return value + ("…" if start + limit < len(clean) else "")


def _active_entity(db: Session, document: KnowledgeDocument) -> bool:
    tenant_id = get_current_tenant_id()
    if document.entity_type == "product":
        return db.scalar(select(Product.id).where(
            Product.id == document.entity_id, Product.tenant_id == tenant_id,
            Product.deleted_at.is_(None), Product.lifecycle_status == "active",
            Product.merged_into_id.is_(None),
        )) is not None
    return db.scalar(select(Service.id).where(
        Service.id == document.entity_id, Service.tenant_id == tenant_id,
        Service.deleted_at.is_(None), Service.status == "active",
    )) is not None


def _eligible_documents(db: Session, *, entity_type: str | None, entity_id: int | None):
    stmt = select(KnowledgeDocument).where(
        KnowledgeDocument.tenant_id == get_current_tenant_id(),
        KnowledgeDocument.confirmed.is_(True), KnowledgeDocument.active.is_(True),
        KnowledgeDocument.status == "published", KnowledgeDocument.withdrawn_at.is_(None),
    )
    if entity_type:
        stmt = stmt.where(KnowledgeDocument.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(KnowledgeDocument.entity_id == entity_id)
    rows = db.scalars(stmt.order_by(KnowledgeDocument.knowledge_version.desc())).all()
    return [row for row in rows if _active_entity(db, row)]


def _entity_terms(db: Session, doc: KnowledgeDocument) -> set[str]:
    terms: set[str] = set()
    if doc.entity_type == "product":
        product = db.scalar(select(Product).where(
            Product.id == doc.entity_id, Product.tenant_id == get_current_tenant_id()
        ))
        if product:
            terms.add(product.canonical_name)
        aliases = db.scalars(select(ProductAlias.alias).where(
            ProductAlias.tenant_id == get_current_tenant_id(),
            ProductAlias.product_id == doc.entity_id, ProductAlias.deleted_at.is_(None),
        )).all()
        terms.update(aliases)
    else:
        service = db.scalar(select(Service).where(
            Service.id == doc.entity_id, Service.tenant_id == get_current_tenant_id()
        ))
        if service:
            terms.add(service.name)
    try:
        terms.update(json.loads(doc.metadata_json or "{}").get("aliases") or [])
    except (TypeError, json.JSONDecodeError):
        pass
    return {term for term in terms if term}


def retrieve(db: Session, data) -> dict:
    if bool(data.entity_type) != bool(data.entity_id):
        raise DomainError("指定实体检索必须同时提供 entity_type 和 entity_id")
    query = data.query.strip()
    documents = _eligible_documents(db, entity_type=data.entity_type, entity_id=data.entity_id)
    if data.entity_id and not documents:
        return {"status": "knowledge_insufficient", "strategy": "entity_exact", "evidence": [], "untrusted_data": True}

    candidates: dict[int, dict] = {}
    normalized_query = normalize_product_text(query)

    # 指定实体当前版本是第一优先；不允许用相似实体替代。
    if data.entity_id:
        for doc in documents:
            candidates[doc.id] = {"doc": doc, "score": 1.0, "match": "entity_current_exact"}

    # 未指定实体时，实体标准名/别名精确命中优先。
    for doc in documents:
        terms = _entity_terms(db, doc)
        normalized_terms = {normalize_product_text(term) for term in terms}
        if normalized_query in normalized_terms:
            candidates[doc.id] = {"doc": doc, "score": 0.96, "match": "entity_name_or_alias"}
        elif any(normalized_query and normalized_query in normalize_product_text(term) for term in terms) or query.lower() in doc.text.lower():
            current = candidates.get(doc.id)
            if current is None or current["score"] < 0.82:
                candidates[doc.id] = {"doc": doc, "score": 0.82, "match": "keyword"}

    vector_state = "not_needed"
    if len(candidates) < data.limit and safe_for_embedding_query(query):
        try:
            adapter = build_embedding_adapter()
            query_vector = adapter.embed(query)
            store = build_vector_store()
            for doc in documents:
                record = db.scalar(select(EmbeddingRecord).where(
                    EmbeddingRecord.tenant_id == get_current_tenant_id(),
                    EmbeddingRecord.document_id == doc.id,
                    EmbeddingRecord.status == "indexed",
                    EmbeddingRecord.embedding_provider == adapter.provider,
                    EmbeddingRecord.embedding_model == adapter.model,
                    EmbeddingRecord.dimension == adapter.dimension,
                    EmbeddingRecord.knowledge_version == doc.knowledge_version,
                ).order_by(EmbeddingRecord.id.desc()))
                if not record or not record.vector_ref:
                    continue
                vector = store.load(record.vector_ref, expected_dimension=adapter.dimension)
                score = max(0.0, _cosine(query_vector.values, vector))
                if score >= 0.08 and (doc.id not in candidates or candidates[doc.id]["score"] < 0.55 + score * 0.25):
                    candidates[doc.id] = {"doc": doc, "score": 0.55 + score * 0.25, "match": "local_vector"}
            vector_state = "local_index"
        except Exception:
            vector_state = "index_failed_fallback"
    elif not safe_for_embedding_query(query):
        vector_state = "unsafe_query_skipped"

    ranked = sorted(candidates.values(), key=lambda item: (-item["score"], item["doc"].id))[:data.limit]
    evidence = [{
        "document_id": item["doc"].id,
        "knowledge_version": item["doc"].knowledge_version,
        "entity_type": item["doc"].entity_type,
        "entity_id": item["doc"].entity_id,
        "source": {"type": item["doc"].source_type, "name": item["doc"].source_name},
        "score": round(item["score"], 4), "match": item["match"],
        "snippet": _snippet(item["doc"].text, query),
    } for item in ranked]
    if evidence:
        strategy = evidence[0]["match"]
        status = "ok" if vector_state != "index_failed_fallback" else "fallback"
    else:
        strategy = "knowledge_insufficient"
        status = "knowledge_insufficient"
    return {
        "status": status, "strategy": strategy, "vector_state": vector_state,
        "evidence": evidence, "untrusted_data": True,
        "instruction_boundary": "evidence_only_no_recommendation",
    }
