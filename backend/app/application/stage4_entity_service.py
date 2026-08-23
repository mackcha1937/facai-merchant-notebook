"""阶段4客户事实/产品实体用例，所有写入仍经统一 Proposal。"""
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.application.conversation_service import (
    _local_date, _load_json, _utc_naive, get_or_create_session, get_or_create_thread,
    proposal_dict,
)
from app.application.fact_extraction_service import ALLOWED_FACT_TYPES, normalize_fact_value
from app.application.product_resolution_service import normalize_product_text, resolve_product
from app.application.stage3_authority import build_authority_snapshot, canonical_json
from app.core.tenant import get_current_owner_id, get_current_tenant_id
from app.domain.errors import ConflictError, DomainError, NotFoundError
from app.infrastructure.models import AgentProposal, LedgerEntry, Message, MessageBlock, PendingAction
from app.repositories import conversations as conversation_repo
from app.repositories import customer_facts as fact_repo
from app.repositories import customers as customer_repo
from app.repositories import products as product_repo
from app.repositories import proposals as proposal_repo


def _action_summary(action: dict) -> str:
    kind = action["type"]
    if kind == "create_product":
        return f"新增产品草稿：{action['canonical_name']}（资料待补充）"
    if kind == "merge_product":
        return f"合并产品 #{action['source_product_id']} → #{action['target_product_id']}"
    if kind == "upsert_customer_fact":
        prefix = "敏感事实" if action.get("sensitivity_level") == "sensitive" else "客户事实"
        return f"{prefix}：{action['display_value']}"
    if kind == "delete_customer_fact":
        return f"撤销客户事实：{action['display_value']}"
    if kind == "record_product_purchase":
        return f"购买{action.get('canonical_name') or action.get('product_name')} {action.get('quantity', 1)}件"
    if kind == "publish_knowledge":
        return f"发布{action.get('entity_type')}知识：{action.get('title')}"
    if kind == "withdraw_knowledge":
        return f"撤回{action.get('entity_type')}知识"
    return kind


def _create_proposal(
    db: Session,
    *,
    parsed: dict,
    original_input: str,
    request_id: str,
    idempotency_key: str,
    block_type: str = "confirm_card",
    status: str = "pending",
    now: datetime | None = None,
) -> dict:
    duplicate = proposal_repo.get_by_idempotency_key(db, idempotency_key)
    if duplicate is None:
        duplicate = proposal_repo.get_by_request_id(db, request_id)
    if duplicate:
        return {"status": duplicate.status, "proposal": proposal_dict(duplicate), "idempotent_replay": True}
    current = _utc_naive(now)
    thread = get_or_create_thread(db)
    session = get_or_create_session(db, thread, now)
    parsed["changes_summary"] = "；".join(_action_summary(item) for item in parsed["actions"])
    parsed.setdefault("precheck", "确认时重新检查事实版本、产品状态和重复项")
    parsed.setdefault("resolved_absolute_dates", {})
    authority = build_authority_snapshot(db, parsed)
    proposal = proposal_repo.create_proposal(
        db, original_input, json.dumps(parsed, ensure_ascii=False), None, status,
        owner_id=get_current_owner_id(), thread_id=thread.id, request_id=request_id,
        idempotency_key=idempotency_key, expires_at=current + timedelta(hours=24),
        resolved_absolute_dates=json.dumps(parsed["resolved_absolute_dates"], ensure_ascii=False),
        data_version=1, authority_snapshot_json=canonical_json(authority), updated_at=current,
    )
    pending = PendingAction(
        tenant_id=get_current_tenant_id(), thread_id=thread.id, proposal_id=proposal.id,
        status="pending", expires_at=proposal.expires_at, created_at=current, updated_at=current,
    )
    db.add(pending)
    db.flush()
    message = Message(
        tenant_id=get_current_tenant_id(), session_id=session.id, role="assistant",
        content="已生成统一确认卡，确认前不会写入。", message_type="block", created_at=current,
    )
    db.add(message)
    db.flush()
    db.add(MessageBlock(
        tenant_id=get_current_tenant_id(), message_id=message.id, block_type=block_type,
        payload_json=json.dumps(proposal_dict(proposal), ensure_ascii=False), state=status,
        data_version=1, proposal_id=proposal.id, created_at=current,
    ))
    thread.last_active_at = current
    db.commit()
    return {"status": status, "proposal": proposal_dict(proposal), "idempotent_replay": False}


def create_product_proposal(db: Session, data) -> dict:
    name = data.canonical_name.strip()
    current = resolve_product(db, name, brand=data.brand, specification=data.specification)
    if current["status"] == "exact":
        raise ConflictError("已存在相同产品，请使用现有产品", {
            "status": "conflict", "conflict_type": "duplicate_product", "product_match": current,
        })
    aliases = []
    seen = set()
    for raw in data.aliases:
        value = raw.strip()
        normalized = normalize_product_text(value)
        if value and normalized and normalized not in seen:
            seen.add(normalized)
            aliases.append(value)
    parsed = {
        "title": "确认新增产品草稿",
        "customer": None,
        "actions": [{
            "type": "create_product", "canonical_name": name, "brand": data.brand,
            "category": data.category, "specification": data.specification, "aliases": aliases,
        }],
    }
    return _create_proposal(
        db, parsed=parsed, original_input=f"新增产品 {name}",
        request_id=data.request_id, idempotency_key=data.idempotency_key,
    )


def create_merge_proposal(db: Session, data) -> dict:
    source = product_repo.get_product(db, data.source_product_id)
    target = product_repo.get_product(db, data.target_product_id)
    if source is None or target is None:
        raise NotFoundError("待合并产品不存在、已停用或已合并")
    if source.id == target.id:
        raise DomainError("不能把产品合并到自身")
    parsed = {
        "title": "确认合并重复产品",
        "customer": None,
        "actions": [{
            "type": "merge_product", "source_product_id": source.id,
            "target_product_id": target.id,
        }],
    }
    return _create_proposal(
        db, parsed=parsed,
        original_input=f"把{source.canonical_name}合并到{target.canonical_name}",
        request_id=data.request_id, idempotency_key=data.idempotency_key,
    )


def create_fact_proposal(db: Session, customer_id: int, data) -> dict:
    customer = customer_repo.get_customer(db, customer_id)
    if customer is None:
        raise NotFoundError("客户不存在或已删除")
    actions = []
    for item in data.facts:
        if item.fact_type not in ALLOWED_FACT_TYPES:
            raise DomainError(f"客户事实类型不在白名单内：{item.fact_type}")
        current = fact_repo.get_current_by_type(db, customer.id, item.fact_type)
        normalized = normalize_fact_value(item.display_value)
        if current and current.normalized_value == normalized:
            continue
        actions.append({
            "type": "upsert_customer_fact", "fact_type": item.fact_type,
            "display_value": item.display_value.strip(), "normalized_value": normalized,
            "evidence_text": item.evidence_text.strip(), "confidence": item.confidence,
            "sensitivity_level": item.sensitivity_level,
            "supersedes_id": current.id if current else None,
            "conflict": bool(current), "previous_value": current.display_value if current else None,
        })
    if not actions:
        raise DomainError("没有需要新增或更新的客户事实")
    parsed = {
        "title": f"确认{customer.display_name}的客户事实",
        "customer": {"customer_id": customer.id, "display_name": customer.display_name},
        "actions": actions,
    }
    return _create_proposal(
        db, parsed=parsed, original_input="；".join(item.evidence_text for item in data.facts),
        request_id=data.request_id, idempotency_key=data.idempotency_key,
    )


def resolve_proposal_product(db: Session, proposal_id: int, data) -> dict:
    proposal = proposal_repo.get_proposal(db, proposal_id)
    if proposal is None or proposal.owner_id != get_current_owner_id():
        raise NotFoundError("产品匹配卡不存在")
    parsed = _load_json(proposal.parsed_json, {})
    if proposal.status == "pending" and parsed.get("resolution_idempotency_key") == data.idempotency_key:
        return {"status": "pending", "proposal": proposal_dict(proposal), "idempotent_replay": True}
    if proposal.status != "resolving" or proposal.data_version != data.data_version:
        raise ConflictError("产品匹配卡状态或版本已变化", {
            "status": "conflict", "conflict_type": "product_resolution_version",
            "proposal": proposal_dict(proposal),
        })

    claimed = db.execute(
        update(AgentProposal).where(
            AgentProposal.id == proposal.id,
            AgentProposal.tenant_id == get_current_tenant_id(),
            AgentProposal.owner_id == get_current_owner_id(),
            AgentProposal.status == "resolving",
            AgentProposal.data_version == data.data_version,
        ).values(status="resolving_claimed")
    ).rowcount
    if claimed != 1:
        db.rollback()
        raise ConflictError("另一设备正在处理产品匹配", {
            "status": "conflict", "conflict_type": "concurrent_product_resolution",
        })
    db.refresh(proposal)
    match = parsed.get("product_match") or {}
    purchase = parsed.get("product_purchase") or {}
    occurred_on = ((parsed.get("resolved_absolute_dates") or {}).get("occurred_on") or {}).get("date")
    action = {
        "type": "record_product_purchase", "quantity": int(purchase.get("quantity") or 1),
        "occurred_on": occurred_on,
    }
    if data.create_new:
        current = resolve_product(
            db, data.canonical_name or purchase.get("query") or "",
            brand=data.brand, specification=data.specification,
        )
        if current["status"] == "exact":
            db.rollback()
            raise ConflictError("确认期间已出现相同产品，请重新选择", {
                "status": "stale", "conflict_type": "product_appeared", "product_match": current,
            })
        action.update({
            "create_product": True,
            "canonical_name": (data.canonical_name or purchase.get("query") or "").strip(),
            "product_name": (data.canonical_name or purchase.get("query") or "").strip(),
            "brand": data.brand, "category": data.category,
            "specification": data.specification, "aliases": [],
        })
    else:
        candidate_ids = {item["id"] for item in match.get("candidates", [])}
        if data.product_id not in candidate_ids:
            db.rollback()
            raise DomainError("只能选择匹配卡中当前展示的候选产品")
        product = product_repo.get_product(db, data.product_id)
        if product is None:
            db.rollback()
            raise ConflictError("候选产品状态已变化，请重新匹配", {"status": "stale"})
        action.update({"product_id": product.id, "product_name": product.canonical_name})

    parsed.setdefault("actions", []).append(action)
    parsed["resolution_required"] = False
    parsed["resolution_idempotency_key"] = data.idempotency_key
    parsed["changes_summary"] = "；".join(_action_summary(item) for item in parsed["actions"])
    proposal.parsed_json = json.dumps(parsed, ensure_ascii=False)
    proposal.status = "pending"
    proposal.data_version += 1
    proposal.updated_at = _utc_naive()
    proposal.authority_snapshot_json = canonical_json(build_authority_snapshot(db, parsed))
    block = conversation_repo.get_block_for_proposal(db, proposal.id)
    if block:
        block.block_type = "confirm_card"
        block.state = "pending"
        block.data_version = proposal.data_version
        block.payload_json = json.dumps(proposal_dict(proposal), ensure_ascii=False)
    pending = conversation_repo.get_pending_for_proposal(db, proposal.id)
    if pending:
        pending.updated_at = proposal.updated_at
    db.commit()
    return {"status": "pending", "proposal": proposal_dict(proposal), "idempotent_replay": False}


def list_products(db: Session) -> list[dict]:
    products = product_repo.list_products(db, include_inactive=True)
    aliases = product_repo.list_aliases(db, [item.id for item in products])
    aliases_by_id: dict[int, list[str]] = {}
    for row in aliases:
        aliases_by_id.setdefault(row.product_id, []).append(row.alias)
    counts = dict(db.execute(
        select(LedgerEntry.product_id, func.count(LedgerEntry.id)).where(
            LedgerEntry.tenant_id == get_current_tenant_id(),
            LedgerEntry.product_id.is_not(None), LedgerEntry.deleted_at.is_(None),
        ).group_by(LedgerEntry.product_id)
    ).all())
    return [
        _product_view(item, aliases_by_id.get(item.id, []), int(counts.get(item.id, 0)))
        for item in products
    ]


def get_product_detail(db: Session, product_id: int) -> dict:
    product = product_repo.get_product(db, product_id, include_replaced=True)
    if product is None:
        raise NotFoundError("产品不存在")
    aliases = [row.alias for row in product_repo.list_aliases(db, [product.id])]
    count = db.scalar(select(func.count(LedgerEntry.id)).where(
        LedgerEntry.tenant_id == get_current_tenant_id(), LedgerEntry.product_id == product.id,
        LedgerEntry.deleted_at.is_(None),
    )) or 0
    return _product_view(product, aliases, int(count))


def _product_view(product, aliases: list[str], purchase_count: int) -> dict:
    return {
        "id": product.id, "canonical_name": product.canonical_name, "name": product.canonical_name,
        "brand": product.brand, "category": product.category,
        "specification": product.specification, "aliases": aliases,
        "lifecycle_status": product.lifecycle_status,
        "knowledge_status": product.knowledge_status,
        "owner_id": product.owner_id, "version": product.version,
        "merged_into_id": product.merged_into_id, "purchase_count": purchase_count,
    }
