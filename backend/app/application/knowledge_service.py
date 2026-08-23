"""阶段5知识 Proposal、确认发布/撤回、版本与本地索引。"""
import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.knowledge_security import validate_knowledge_input
from app.application.product_resolution_service import normalize_product_text
from app.application.stage4_entity_service import _create_proposal
from app.core.tenant import get_current_owner_id, get_current_tenant_id
from app.core.rbac import require_admin
from app.domain.errors import ConflictError, DomainError, NotFoundError
from app.infrastructure.embedding import (
    EmbeddingError, LocalDeterministicEmbedding, SqliteVectorStore,
)
from app.infrastructure.models import (
    EmbeddingRecord, KnowledgeChunk, KnowledgeDocument, Product,
    ProductAlias, ProductKnowledgeVersion, ReleaseAudit, Service,
    ServiceKnowledgeVersion, utcnow,
)


VERSION_MODELS = {
    "product": ProductKnowledgeVersion,
    "service": ServiceKnowledgeVersion,
}


def build_embedding_adapter():
    return LocalDeterministicEmbedding()


def build_vector_store():
    return SqliteVectorStore()


def _checksum(payload: dict) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _entity(db: Session, entity_type: str, entity_id: int, *, require_active: bool = True):
    tenant_id = get_current_tenant_id()
    if entity_type == "product":
        row = db.scalar(select(Product).where(
            Product.id == entity_id, Product.tenant_id == tenant_id, Product.deleted_at.is_(None)
        ))
        active = row is not None and row.lifecycle_status == "active" and row.merged_into_id is None
    elif entity_type == "service":
        row = db.scalar(select(Service).where(
            Service.id == entity_id, Service.tenant_id == tenant_id, Service.deleted_at.is_(None)
        ))
        active = row is not None and row.status == "active"
    else:
        raise DomainError("知识实体类型无效")
    if row is None:
        raise NotFoundError("知识实体不存在或不属于当前店铺")
    if require_active and not active:
        raise DomainError("停用、草稿、已合并或删除实体不能发布/检索知识")
    return row


def _current_version(db: Session, entity_type: str, entity_id: int):
    model = VERSION_MODELS[entity_type]
    return db.scalar(select(model).where(
        model.tenant_id == get_current_tenant_id(), model.entity_id == entity_id,
        model.status == "published",
    ).order_by(model.version.desc()))


def _current_document(db: Session, entity_type: str, entity_id: int):
    return db.scalar(select(KnowledgeDocument).where(
        KnowledgeDocument.tenant_id == get_current_tenant_id(),
        KnowledgeDocument.entity_type == entity_type,
        KnowledgeDocument.entity_id == entity_id,
        KnowledgeDocument.confirmed.is_(True), KnowledgeDocument.active.is_(True),
        KnowledgeDocument.status == "published",
    ).order_by(KnowledgeDocument.knowledge_version.desc()))


def _entity_name(entity_type: str, entity) -> str:
    return entity.canonical_name if entity_type == "product" else entity.name


def create_knowledge_proposal(db: Session, data) -> dict:
    require_admin()
    entity = _entity(db, data.entity_type, data.entity_id)
    title = validate_knowledge_input(
        db, data.title, source_type=data.source_type, source_name=data.source_name,
    )
    content = validate_knowledge_input(
        db, data.content, source_type=data.source_type, source_name=data.source_name,
    )
    aliases = []
    seen = set()
    for value in data.aliases:
        cleaned = value.strip()
        normalized = normalize_product_text(cleaned)
        if cleaned and normalized and normalized not in seen and len(cleaned) <= 100:
            seen.add(normalized)
            aliases.append(cleaned)
    payload = {
        "entity_type": data.entity_type, "entity_id": entity.id,
        "title": title, "content": content, "source_type": data.source_type,
        "source_name": data.source_name.strip(), "aliases": aliases,
    }
    checksum = _checksum(payload)
    current = _current_version(db, data.entity_type, entity.id)
    if current and current.checksum == checksum:
        raise ConflictError("知识内容未变化，无需重复生成版本", {
            "status": "conflict", "conflict_type": "unchanged_checksum",
            "knowledge_version": current.version,
        })
    action = {
        "type": "publish_knowledge", **payload, "knowledge_checksum": checksum,
        "current_version_id": current.id if current else None,
    }
    return _create_proposal(
        db,
        parsed={
            "title": f"确认发布{_entity_name(data.entity_type, entity)}知识", "customer": None,
            "actions": [action], "precheck": "确认时重新校验管理员权限、实体状态、当前版本、checksum 与全部安全门禁",
        },
        original_input=f"发布{data.entity_type}知识：{title}",
        request_id=data.request_id, idempotency_key=data.idempotency_key,
        block_type="knowledge_confirm_card",
    )


def create_withdraw_proposal(db: Session, data) -> dict:
    require_admin()
    entity = _entity(db, data.entity_type, data.entity_id, require_active=False)
    current = _current_version(db, data.entity_type, entity.id)
    if current is None:
        raise DomainError("当前没有可撤回的已发布知识")
    action = {
        "type": "withdraw_knowledge", "entity_type": data.entity_type,
        "entity_id": entity.id, "current_version_id": current.id,
        "knowledge_checksum": current.checksum, "reason": data.reason.strip(),
    }
    return _create_proposal(
        db,
        parsed={
            "title": f"确认撤回{_entity_name(data.entity_type, entity)}知识", "customer": None,
            "actions": [action], "precheck": "确认时重新校验管理员权限、实体状态与当前知识版本",
        },
        original_input=f"撤回知识：{data.reason.strip()}",
        request_id=data.request_id, idempotency_key=data.idempotency_key,
        block_type="knowledge_confirm_card",
    )


def authority_state(db: Session, entity_type: str, entity_id: int) -> dict:
    entity = _entity(db, entity_type, entity_id, require_active=False)
    current = _current_version(db, entity_type, entity_id)
    return {
        "entity_type": entity_type, "entity_id": entity.id,
        "entity_status": entity.lifecycle_status if entity_type == "product" else entity.status,
        "entity_version": getattr(entity, "version", None),
        "knowledge": ({
            "id": current.id, "version": current.version, "status": current.status,
            "checksum": current.checksum, "updated_at": current.updated_at.isoformat() if current.updated_at else None,
        } if current else None),
    }


def validate_action(db: Session, action) -> dict:
    if action.entity_type not in VERSION_MODELS or not action.entity_id:
        return {"type": action.type, "ok": False, "error": "知识实体无效"}
    try:
        _entity(db, action.entity_type, action.entity_id, require_active=action.type == "publish_knowledge")
        current = _current_version(db, action.entity_type, action.entity_id)
        if action.type == "publish_knowledge":
            title = validate_knowledge_input(
                db, action.title or "", source_type=action.source_type or "", source_name=action.source_name or "",
            )
            cleaned = validate_knowledge_input(
                db, action.content or "", source_type=action.source_type or "", source_name=action.source_name or "",
            )
            payload = {
                "entity_type": action.entity_type, "entity_id": action.entity_id,
                "title": title, "content": cleaned,
                "source_type": action.source_type, "source_name": (action.source_name or "").strip(),
                "aliases": action.aliases,
            }
            if _checksum(payload) != action.knowledge_checksum:
                raise DomainError("知识候选校验和不一致")
            if current and current.checksum == action.knowledge_checksum:
                raise DomainError("知识内容未变化，拒绝重复发布")
        elif action.type == "withdraw_knowledge":
            if current is None or current.id != action.current_version_id or current.checksum != action.knowledge_checksum:
                raise DomainError("当前知识版本已变化，请重新生成撤回确认卡")
        return {"type": action.type, "ok": True, "error": None, "preview": {
            "entity_type": action.entity_type, "entity_id": action.entity_id,
            "next_version": (current.version + 1) if current and action.type == "publish_knowledge" else 1,
        }}
    except (DomainError, NotFoundError) as exc:
        return {"type": action.type, "ok": False, "error": str(exc)}


def _index_document(db: Session, version, document: KnowledgeDocument, chunk: KnowledgeChunk) -> str:
    adapter = build_embedding_adapter()
    store = build_vector_store()
    existing = db.scalar(select(EmbeddingRecord).where(
        EmbeddingRecord.tenant_id == get_current_tenant_id(),
        EmbeddingRecord.document_id == document.id,
        EmbeddingRecord.embedding_provider == adapter.provider,
        EmbeddingRecord.embedding_model == adapter.model,
        EmbeddingRecord.checksum == chunk.checksum,
    ))
    if existing and existing.status == "indexed":
        version.embedding_status = "indexed"
        return "checksum_unchanged"
    now = utcnow()
    try:
        vector = adapter.embed(chunk.text)
        if vector.dimension != adapter.dimension or len(vector.values) != adapter.dimension:
            raise EmbeddingError("dimension_mismatch")
        vector_ref = store.put(document_id=document.id, chunk_id=chunk.id, checksum=chunk.checksum, vector=vector)
        record = existing or EmbeddingRecord(
            tenant_id=get_current_tenant_id(), document_id=document.id, chunk_id=chunk.id,
            knowledge_version=document.knowledge_version, embedding_provider=vector.provider,
            embedding_model=vector.model, dimension=vector.dimension, checksum=chunk.checksum,
            created_at=now,
        )
        record.vector_ref = vector_ref
        record.dimension = vector.dimension
        record.status = "indexed"
        record.error_code = None
        record.indexed_at = now
        record.updated_at = now
        if existing is None:
            db.add(record)
        version.embedding_status = "indexed"
        return "indexed"
    except Exception as exc:  # local adapter/index failure must not fabricate evidence
        code = str(exc)[:50] or "index_failed"
        record = existing or EmbeddingRecord(
            tenant_id=get_current_tenant_id(), document_id=document.id, chunk_id=chunk.id,
            knowledge_version=document.knowledge_version,
            embedding_provider=getattr(adapter, "provider", "local-error"),
            embedding_model=getattr(adapter, "model", "local-error"),
            dimension=getattr(adapter, "dimension", None), checksum=chunk.checksum, created_at=now,
        )
        record.status = "failed"
        record.error_code = code
        record.vector_ref = None
        record.updated_at = now
        if existing is None:
            db.add(record)
        version.embedding_status = "index_failed"
        return "index_failed"


def execute_action(db: Session, action, proposal) -> dict:
    if action.type == "publish_knowledge":
        return _publish(db, action, proposal)
    if action.type == "withdraw_knowledge":
        return _withdraw(db, action, proposal)
    raise DomainError("未知知识操作")


def _publish(db: Session, action, proposal) -> dict:
    entity = _entity(db, action.entity_type, action.entity_id)
    model = VERSION_MODELS[action.entity_type]
    current = _current_version(db, action.entity_type, action.entity_id)
    next_version = (current.version + 1) if current else 1
    now = utcnow()
    if current:
        current.status = "superseded"
        current.embedding_status = "superseded"
        current.updated_at = now
        old_doc = _current_document(db, action.entity_type, action.entity_id)
        if old_doc:
            old_doc.active = False
            old_doc.status = "superseded"
            old_doc.updated_at = now
            for old_embedding in db.scalars(select(EmbeddingRecord).where(
                EmbeddingRecord.tenant_id == get_current_tenant_id(),
                EmbeddingRecord.document_id == old_doc.id,
            )).all():
                old_embedding.status = "superseded"
                old_embedding.updated_at = now
            for old_chunk in db.scalars(select(KnowledgeChunk).where(
                KnowledgeChunk.tenant_id == get_current_tenant_id(), KnowledgeChunk.document_id == old_doc.id
            )).all():
                old_chunk.status = "superseded"
                old_chunk.updated_at = now
    payload = {
        "title": action.title, "content": action.content, "aliases": action.aliases,
        "entity_name": _entity_name(action.entity_type, entity),
    }
    version = model(
        tenant_id=get_current_tenant_id(), entity_id=entity.id, version=next_version,
        content_json=json.dumps(payload, ensure_ascii=False),
        source_refs=json.dumps([{"type": action.source_type, "name": action.source_name}], ensure_ascii=False),
        owner_confirmed_at=now, published_at=now, embedding_status="pending",
        status="published", checksum=action.knowledge_checksum,
        source_type=action.source_type, source_name=action.source_name,
        supersedes_id=current.id if current else None, created_by=get_current_owner_id(),
        created_at=now, updated_at=now,
    )
    db.add(version)
    db.flush()
    text = f"{action.title}\n{action.content}".strip()
    document = KnowledgeDocument(
        tenant_id=get_current_tenant_id(), entity_type=action.entity_type, entity_id=entity.id,
        knowledge_version=next_version, text=text,
        metadata_json=json.dumps({
            "version_id": version.id, "source_type": action.source_type,
            "source_name": action.source_name, "aliases": action.aliases,
            "proposal_id": proposal.id, "untrusted_data": True,
        }, ensure_ascii=False),
        status="published", checksum=action.knowledge_checksum,
        source_type=action.source_type, source_name=action.source_name,
        confirmed=True, active=True, created_at=now, updated_at=now,
    )
    db.add(document)
    db.flush()
    chunk_checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
    chunk = KnowledgeChunk(
        tenant_id=get_current_tenant_id(), document_id=document.id, chunk_index=0,
        text=text, metadata_json=document.metadata_json, status="active",
        checksum=chunk_checksum, created_at=now, updated_at=now,
    )
    db.add(chunk)
    db.flush()
    index_status = _index_document(db, version, document, chunk)
    if action.entity_type == "product":
        entity.knowledge_status = "complete"
        entity.version += 1
        for alias in action.aliases:
            normalized = normalize_product_text(alias)
            duplicate = db.scalar(select(ProductAlias.id).where(
                ProductAlias.tenant_id == get_current_tenant_id(), ProductAlias.product_id == entity.id,
                ProductAlias.normalized_alias == normalized, ProductAlias.deleted_at.is_(None),
            ))
            if not duplicate:
                db.add(ProductAlias(
                    tenant_id=get_current_tenant_id(), product_id=entity.id, alias=alias,
                    normalized_alias=normalized, source="knowledge_owner_confirmed", created_at=now,
                ))
    db.add(ReleaseAudit(
        tenant_id=get_current_tenant_id(), release_type="knowledge", release_id=version.id,
        actor_id=get_current_owner_id(), action="publish",
        before_json=json.dumps({"version_id": current.id if current else None}, ensure_ascii=False),
        after_json=json.dumps({"version_id": version.id, "version": next_version, "checksum": version.checksum, "index_status": index_status}, ensure_ascii=False),
        created_at=now,
    ))
    return {
        "type": "publish_knowledge", "message": "知识已确认发布。",
        "entity_type": action.entity_type, "entity_id": entity.id,
        "knowledge_version": next_version, "document_id": document.id,
        "checksum": version.checksum, "index_status": index_status,
    }


def _withdraw(db: Session, action, proposal) -> dict:
    del proposal
    current = _current_version(db, action.entity_type, action.entity_id)
    if current is None or current.id != action.current_version_id:
        raise DomainError("知识版本已变化，撤回失败")
    now = utcnow()
    current.status = "withdrawn"
    current.embedding_status = "withdrawn"
    current.withdrawn_at = now
    current.updated_at = now
    document = _current_document(db, action.entity_type, action.entity_id)
    if document:
        document.status = "withdrawn"
        document.active = False
        document.withdrawn_at = now
        document.updated_at = now
        for embedding in db.scalars(select(EmbeddingRecord).where(
            EmbeddingRecord.tenant_id == get_current_tenant_id(),
            EmbeddingRecord.document_id == document.id,
        )).all():
            embedding.status = "withdrawn"
            embedding.updated_at = now
        for chunk in db.scalars(select(KnowledgeChunk).where(
            KnowledgeChunk.tenant_id == get_current_tenant_id(), KnowledgeChunk.document_id == document.id
        )).all():
            chunk.status = "withdrawn"
            chunk.updated_at = now
    if action.entity_type == "product":
        entity = _entity(db, "product", action.entity_id, require_active=False)
        entity.knowledge_status = "incomplete"
        entity.version += 1
    db.add(ReleaseAudit(
        tenant_id=get_current_tenant_id(), release_type="knowledge", release_id=current.id,
        actor_id=get_current_owner_id(), action="withdraw",
        before_json=json.dumps({"status": "published", "version": current.version}, ensure_ascii=False),
        after_json=json.dumps({"status": "withdrawn", "reason": action.reason}, ensure_ascii=False),
        created_at=now,
    ))
    return {
        "type": "withdraw_knowledge", "message": "知识已撤回，不再参与检索。",
        "entity_type": action.entity_type, "entity_id": action.entity_id,
        "knowledge_version": current.version,
    }


def reindex_current(db: Session, entity_type: str, entity_id: int) -> dict:
    require_admin()
    _entity(db, entity_type, entity_id)
    version = _current_version(db, entity_type, entity_id)
    document = _current_document(db, entity_type, entity_id)
    if version is None or document is None:
        raise DomainError("没有可重建索引的当前已发布知识")
    chunk = db.scalar(select(KnowledgeChunk).where(
        KnowledgeChunk.tenant_id == get_current_tenant_id(), KnowledgeChunk.document_id == document.id,
        KnowledgeChunk.status == "active",
    ).order_by(KnowledgeChunk.chunk_index))
    if chunk is None:
        raise DomainError("当前知识缺少有效 Chunk")
    status = _index_document(db, version, document, chunk)
    db.add(ReleaseAudit(
        tenant_id=get_current_tenant_id(), release_type="knowledge", release_id=version.id,
        actor_id=get_current_owner_id(), action="reindex", before_json=None,
        after_json=json.dumps({"status": status, "checksum": chunk.checksum}, ensure_ascii=False),
        created_at=utcnow(),
    ))
    db.commit()
    return {"status": status, "document_id": document.id, "knowledge_version": version.version}


def list_knowledge(db: Session, *, include_history: bool = True) -> list[dict]:
    tenant_id = get_current_tenant_id()
    stmt = select(KnowledgeDocument).where(KnowledgeDocument.tenant_id == tenant_id)
    if not include_history:
        stmt = stmt.where(KnowledgeDocument.confirmed.is_(True), KnowledgeDocument.active.is_(True))
    rows = db.scalars(stmt.order_by(KnowledgeDocument.entity_type, KnowledgeDocument.entity_id, KnowledgeDocument.knowledge_version.desc())).all()
    output = []
    for row in rows:
        embedding = db.scalar(select(EmbeddingRecord).where(
            EmbeddingRecord.tenant_id == tenant_id, EmbeddingRecord.document_id == row.id
        ).order_by(EmbeddingRecord.id.desc()))
        output.append({
            "document_id": row.id, "entity_type": row.entity_type, "entity_id": row.entity_id,
            "knowledge_version": row.knowledge_version, "status": row.status,
            "confirmed": row.confirmed, "active": row.active, "source_type": row.source_type,
            "source_name": row.source_name, "checksum": row.checksum,
            "index_status": embedding.status if embedding else "not_indexed",
            "embedding": ({
                "provider": embedding.embedding_provider, "model": embedding.embedding_model,
                "dimension": embedding.dimension,
            } if embedding else None),
            "created_at": row.created_at.isoformat(),
        })
    return output


def list_owner_knowledge(db: Session) -> list[dict]:
    """店主只读简化视图：不返回 checksum、向量引用或可调技术参数。"""
    return [{
        "document_id": item["document_id"], "entity_type": item["entity_type"],
        "entity_id": item["entity_id"], "knowledge_version": item["knowledge_version"],
        "status": item["status"], "confirmed": item["confirmed"], "active": item["active"],
        "source_type": item["source_type"], "source_name": item["source_name"],
        "index_status": item["index_status"],
    } for item in list_knowledge(db, include_history=False)]


def owner_status(db: Session) -> dict:
    tenant_id = get_current_tenant_id()
    published = db.scalar(select(func.count(KnowledgeDocument.id)).where(
        KnowledgeDocument.tenant_id == tenant_id, KnowledgeDocument.confirmed.is_(True),
        KnowledgeDocument.active.is_(True), KnowledgeDocument.status == "published",
    )) or 0
    indexed = db.scalar(select(func.count(EmbeddingRecord.id)).join(
        KnowledgeDocument, KnowledgeDocument.id == EmbeddingRecord.document_id
    ).where(
        EmbeddingRecord.tenant_id == tenant_id, EmbeddingRecord.status == "indexed",
        KnowledgeDocument.tenant_id == tenant_id, KnowledgeDocument.confirmed.is_(True),
        KnowledgeDocument.active.is_(True), KnowledgeDocument.status == "published",
    )) or 0
    failed = db.scalar(select(func.count(EmbeddingRecord.id)).join(
        KnowledgeDocument, KnowledgeDocument.id == EmbeddingRecord.document_id
    ).where(
        EmbeddingRecord.tenant_id == tenant_id, EmbeddingRecord.status == "failed",
        KnowledgeDocument.tenant_id == tenant_id, KnowledgeDocument.confirmed.is_(True),
        KnowledgeDocument.active.is_(True), KnowledgeDocument.status == "published",
    )) or 0
    return {
        "knowledge_complete_count": published,
        "embedding": {"status": "local_only", "indexed": indexed, "failed": failed},
        "rag": {"status": "available" if published else "knowledge_insufficient", "result_limit": "3-5"},
        "read_only": True,
        "external_embedding_used": False,
        "recommendation_built": False,
    }
