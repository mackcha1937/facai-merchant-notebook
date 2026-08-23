"""阶段3持续主会话、按日 Session、历史分页和受控解析。"""
import json
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.relative_dates import resolve_relative_date, shanghai_now
from app.application.stage3_authority import build_authority_snapshot, canonical_json
from app.core.tenant import get_current_owner_id, get_current_tenant_id
from app.domain.errors import DomainError
from app.infrastructure.models import (
    AgentProposal,
    ContextSummary,
    ConversationSession,
    ConversationThread,
    EntityMention,
    Message,
    MessageBlock,
    PendingAction,
)
from app.repositories import conversations as conversation_repo
from app.repositories import customers as customer_repo
from app.repositories import customer_facts as fact_repo
from app.repositories import proposals as proposal_repo
from app.repositories import services as service_repo
from app.application.fact_extraction_service import extract_fact_candidates
from app.application.product_resolution_service import extract_product_purchase, resolve_product


def _utc_naive(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is not None:
        current = current.astimezone(timezone.utc).replace(tzinfo=None)
    return current


def _local_date(value: datetime | None = None) -> str:
    if value is None:
        return shanghai_now().date().isoformat()
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(shanghai_now().tzinfo).date().isoformat()


def get_or_create_thread(db: Session, owner_id: int | None = None) -> ConversationThread:
    owner_id = owner_id or get_current_owner_id()
    existing = conversation_repo.get_thread(db, owner_id)
    if existing is not None:
        return existing
    thread = ConversationThread(
        tenant_id=get_current_tenant_id(), owner_id=owner_id, last_active_at=_utc_naive()
    )
    db.add(thread)
    try:
        db.commit()
        db.refresh(thread)
        return thread
    except IntegrityError:
        db.rollback()
        existing = conversation_repo.get_thread(db, owner_id)
        if existing is None:
            raise
        return existing


def get_or_create_session(
    db: Session, thread: ConversationThread, now: datetime | None = None
) -> ConversationSession:
    session_date = _local_date(now)
    existing = conversation_repo.get_session(db, thread.id, session_date)
    if existing is not None:
        return existing
    session = ConversationSession(
        tenant_id=get_current_tenant_id(),
        thread_id=thread.id,
        session_date=session_date,
        timezone="Asia/Shanghai",
        started_at=_utc_naive(now),
    )
    db.add(session)
    try:
        db.commit()
        db.refresh(session)
        return session
    except IntegrityError:
        db.rollback()
        existing = conversation_repo.get_session(db, thread.id, session_date)
        if existing is None:
            raise
        return existing


def get_main_thread(db: Session, now: datetime | None = None) -> dict:
    thread = get_or_create_thread(db)
    session = get_or_create_session(db, thread, now)
    return {
        "id": thread.id,
        "owner_id": thread.owner_id,
        "session": _session_dict(session),
        "timezone": "Asia/Shanghai",
    }


def _session_dict(session: ConversationSession) -> dict:
    return {
        "id": session.id,
        "session_date": session.session_date,
        "timezone": session.timezone,
        "started_at": session.started_at.isoformat() if session.started_at else None,
    }


def _load_json(raw: str | None, fallback):
    try:
        return json.loads(raw) if raw else fallback
    except (TypeError, json.JSONDecodeError):
        return fallback


def proposal_dict(proposal: AgentProposal) -> dict:
    parsed = _load_json(proposal.parsed_json, {})
    dates = _load_json(proposal.resolved_absolute_dates, {})
    return {
        "id": proposal.id,
        "status": proposal.status,
        "request_id": proposal.request_id,
        "data_version": proposal.data_version,
        "expires_at": proposal.expires_at.isoformat() if proposal.expires_at else None,
        "resolved_absolute_dates": dates,
        "absolute_date": (dates.get("occurred_on") or {}).get("date"),
        "original_expression": proposal.original_input,
        "title": parsed.get("title", "确认本次记账"),
        "changes_summary": parsed.get("changes_summary", ""),
        "precheck": parsed.get("precheck", "已读取当前权威数据"),
        "actions": parsed.get("actions", []),
        "customer": parsed.get("customer"),
        "product_match": parsed.get("product_match"),
        "resolution_required": parsed.get("resolution_required", False),
        "resolution_idempotency_key": parsed.get("resolution_idempotency_key"),
        "fact_extraction_source": parsed.get("fact_extraction_source"),
        "result": _load_json(proposal.result_json, None),
    }


def _block_dict(block: MessageBlock) -> dict:
    payload = _load_json(block.payload_json, {})
    return {
        "id": block.id,
        "block_type": block.block_type,
        "state": block.state,
        "data_version": block.data_version,
        "proposal_id": block.proposal_id,
        "payload": payload,
    }


def _message_dict(message: Message, session: ConversationSession, blocks: list[MessageBlock]) -> dict:
    return {
        "id": message.id,
        "session_id": session.id,
        "session_date": session.session_date,
        "role": message.role,
        "content": message.content,
        "message_type": message.message_type,
        "created_at": message.created_at.isoformat(),
        "read_at": message.read_at.isoformat() if message.read_at else None,
        "blocks": [_block_dict(block) for block in blocks],
    }


def history(db: Session, before: int | None = None, limit: int = 30) -> dict:
    thread = get_or_create_thread(db)
    safe_limit = min(max(limit, 1), 100)
    rows = conversation_repo.list_messages(db, thread.id, before=before, limit=safe_limit + 1)
    has_more = len(rows) > safe_limit
    rows = rows[:safe_limit]
    rows.reverse()
    blocks = conversation_repo.list_blocks(db, [message.id for message, _ in rows])
    messages = [_message_dict(message, session, blocks.get(message.id, [])) for message, session in rows]
    return {
        "thread_id": thread.id,
        "timezone": "Asia/Shanghai",
        "messages": messages,
        "next_cursor": messages[0]["id"] if has_more and messages else None,
        "has_more": has_more,
    }


def _resolve_customer(db: Session, text: str):
    candidates = []
    for customer in customer_repo.list_customers(db):
        names = [customer.display_name] + [a.alias for a in customer.aliases if a.deleted_at is None]
        hits = [name for name in names if name and name in text]
        if hits:
            candidates.append((max(hits, key=len), customer))
    candidates.sort(key=lambda item: len(item[0]), reverse=True)
    if not candidates:
        return None, None
    if len(candidates) > 1 and len(candidates[0][0]) == len(candidates[1][0]):
        raise DomainError("匹配到多个客户，请写出更明确的客户称呼")
    return candidates[0][1], candidates[0][0]


def _quantity_after(text: str, name: str) -> int:
    match = re.search(rf"{re.escape(name)}[^，。；;]{{0,12}}?(\d+)\s*次", text)
    return int(match.group(1)) if match else 1


def _controlled_parse(db: Session, text: str, now: datetime | None = None) -> tuple[dict | None, list[dict]]:
    customer, surface = _resolve_customer(db, text)
    if customer is None:
        product_management = _parse_product_management(db, text)
        return (product_management, []) if product_management else (None, [])
    actions = []
    mentions = [{"entity_type": "customer", "entity_id": customer.id, "surface_text": surface}]
    for service in service_repo.list_services(db):
        if service.status != "active" or service.name not in text:
            continue
        action_type = "record_one_time_service" if "一次性" in text else "consume_service"
        actions.append(
            {
                "type": action_type,
                "service_id": service.id,
                "service_name": service.name,
                "quantity": _quantity_after(text, service.name),
            }
        )
        mentions.append({"entity_type": "service", "entity_id": service.id, "surface_text": service.name})

    adapter = None
    from app.core.config import get_settings

    if get_settings().is_model_configured:
        from app.infrastructure.llm.deepseek import DeepSeekAdapter

        adapter = DeepSeekAdapter()
    facts, fact_source = extract_fact_candidates(db, customer.id, text, adapter=adapter)
    for fact in facts:
        actions.append({"type": "upsert_customer_fact", **fact})

    delete_match = re.search(r"(?:把)?[^，。；;]{0,12}?([^，。；;]{1,12}?)(?:标签|事实)?(?:删掉|删除|移除)", text)
    if delete_match:
        keyword = delete_match.group(1).replace(customer.display_name, "").replace(surface or "", "").strip("的 ")
        for fact in fact_repo.list_current(db, customer.id):
            if (
                fact.display_value in keyword or keyword in fact.display_value
                or ("敏感" in keyword and fact.fact_type in {"skin_sensitivity", "skin_condition"})
            ):
                actions.append({
                    "type": "delete_customer_fact", "fact_id": fact.id,
                    "fact_type": fact.fact_type, "display_value": fact.display_value,
                    "evidence_text": text,
                })

    purchase = extract_product_purchase(text)
    product_match = None
    if purchase:
        product_match = resolve_product(db, purchase["query"])
        if product_match["status"] == "exact":
            product = product_match["matched"]
            actions.append({
                "type": "record_product_purchase",
                "product_id": product["id"],
                "product_name": product["canonical_name"],
                "quantity": purchase["quantity"],
            })
            mentions.append({
                "entity_type": "product", "entity_id": product["id"],
                "surface_text": purchase["query"],
            })

    if not actions and not purchase:
        return None, mentions
    resolved = resolve_relative_date(text, now.astimezone(shanghai_now().tzinfo) if now and now.tzinfo else now)
    for action in actions:
        if action["type"] in {"consume_service", "record_one_time_service", "record_product_purchase"}:
            action["occurred_on"] = resolved["date"]
    changes = "；".join(_stage4_action_summary(a) for a in actions)
    resolution_required = bool(purchase and product_match and product_match["status"] != "exact")
    if resolution_required:
        changes = "；".join(filter(None, [changes, f"待确认产品：{purchase['query']}"]))
    parsed = {
        "title": f"确认{customer.display_name}的客户事实和业务记录",
        "changes_summary": changes,
        "precheck": "确认时将重新检查客户、事实版本、产品状态、套餐余额与数据版本",
        "customer": {"customer_id": customer.id, "display_name": customer.display_name},
        "actions": actions,
        "resolved_absolute_dates": {"occurred_on": resolved},
        "product_match": product_match,
        "product_purchase": purchase,
        "resolution_required": resolution_required,
        "fact_extraction_source": fact_source,
    }
    return parsed, mentions


def _parse_product_management(db: Session, text: str) -> dict | None:
    create = re.search(r"(?:新增|添加|创建)(?:一个)?产品[：:]?\s*([^，。；;]+)", text)
    if create:
        name = create.group(1).strip()
        if not name:
            return None
        return {
            "title": "确认新增产品草稿",
            "changes_summary": f"新增产品草稿：{name}（资料待补充）",
            "precheck": "确认时重新检查重复产品；不会创建知识或 RAG 索引",
            "customer": None,
            "actions": [{"type": "create_product", "canonical_name": name, "aliases": []}],
            "resolved_absolute_dates": {},
            "resolution_required": False,
        }
    merge = re.search(r"把\s*([^，。；;]+?)\s*合并到\s*([^，。；;]+)", text)
    if merge:
        source_match = resolve_product(db, merge.group(1).strip())
        target_match = resolve_product(db, merge.group(2).strip())
        if source_match["status"] != "exact" or target_match["status"] != "exact":
            raise DomainError("产品合并需要两个可精确匹配的产品名称")
        source = source_match["matched"]
        target = target_match["matched"]
        return {
            "title": "确认合并重复产品",
            "changes_summary": f"合并产品：{source['name']} → {target['name']}",
            "precheck": "确认时重新检查产品版本与关联账本",
            "customer": None,
            "actions": [{
                "type": "merge_product", "source_product_id": source["id"],
                "target_product_id": target["id"],
            }],
            "resolved_absolute_dates": {},
            "resolution_required": False,
        }
    return None


def _stage4_action_summary(action: dict) -> str:
    if action["type"] == "upsert_customer_fact":
        prefix = "敏感事实" if action.get("sensitivity_level") == "sensitive" else "客户事实"
        return f"{prefix}：{action.get('display_value')}"
    if action["type"] == "delete_customer_fact":
        return f"撤销客户事实：{action.get('display_value')}"
    if action["type"] == "record_product_purchase":
        return f"购买{action.get('product_name')} {action.get('quantity', 1)}件"
    return f"{action.get('service_name', action['type'])} {action.get('quantity', 1)} 次"


def _save_mentions(db: Session, message_id: int, mentions: list[dict]) -> None:
    for mention in mentions:
        db.add(EntityMention(tenant_id=get_current_tenant_id(), message_id=message_id, **mention))


def _update_summary(db: Session, session: ConversationSession, mentions: list[dict], pending_id: int | None) -> None:
    summary = conversation_repo.get_summary(db, session.id)
    entity_ids = sorted({f"{m['entity_type']}:{m['entity_id']}" for m in mentions if m.get("entity_id")})
    if summary is None:
        summary = ContextSummary(
            tenant_id=get_current_tenant_id(), session_id=session.id, version=1
        )
        db.add(summary)
    else:
        previous = set(_load_json(summary.entity_ids, []))
        entity_ids = sorted(previous | set(entity_ids))
        summary.version += 1
    summary.topics = json.dumps(["账本操作"], ensure_ascii=False)
    summary.entity_ids = json.dumps(entity_ids, ensure_ascii=False)
    pending_ids = set(_load_json(summary.pending_ids, []))
    if pending_id:
        pending_ids.add(pending_id)
    summary.pending_ids = json.dumps(sorted(pending_ids), ensure_ascii=False)
    summary.generated_at = _utc_naive()


def chat_turn(db: Session, data, now: datetime | None = None) -> dict:
    duplicate = proposal_repo.get_by_idempotency_key(db, data.idempotency_key)
    if duplicate is None:
        duplicate = proposal_repo.get_by_request_id(db, data.request_id)
    if duplicate is not None:
        return {"status": duplicate.status, "idempotent_replay": True, "proposal": proposal_dict(duplicate)}
    confirmed = proposal_repo.get_by_confirmation_idempotency_key(db, data.idempotency_key)
    if confirmed is not None:
        return {
            "status": "confirmed", "idempotent_replay": True,
            "proposal": proposal_dict(confirmed),
            "result": _load_json(confirmed.result_json, {}),
        }
    if conversation_repo.get_message_by_request(db, f"cancel-{data.idempotency_key}"[:64]) is not None:
        return {"status": "cancelled", "idempotent_replay": True, "proposal": None}
    if conversation_repo.get_message_by_request(db, data.request_id) is not None:
        return {"status": "needs_clarification", "idempotent_replay": True, "proposal": None}

    voice_command = _handle_pending_voice_command(db, data, now)
    if voice_command is not None:
        return voice_command

    thread = get_or_create_thread(db)
    session = get_or_create_session(db, thread, now)
    text = data.text.strip()
    parsed, mentions = _controlled_parse(db, text, now)
    created_at = _utc_naive(now)
    owner_message = Message(
        tenant_id=get_current_tenant_id(), session_id=session.id, role="owner",
        content=text, message_type="text", request_id=data.request_id, created_at=created_at,
    )
    db.add(owner_message)
    db.flush()
    _save_mentions(db, owner_message.id, mentions)

    if parsed is None:
        assistant_text = "我已保留这条消息，但还不能确定客户和可记账的服务，请补充客户称呼与已有服务名称。"
        assistant = Message(
            tenant_id=get_current_tenant_id(), session_id=session.id, role="assistant",
            content=assistant_text, message_type="text", created_at=created_at,
        )
        db.add(assistant)
        thread.last_active_at = created_at
        _update_summary(db, session, mentions, None)
        db.commit()
        return {"status": "needs_clarification", "proposal": None, "message": assistant_text}

    authority = build_authority_snapshot(db, parsed)
    expires_at = created_at + timedelta(hours=24)
    proposal_status = "resolving" if parsed.get("resolution_required") else "pending"
    proposal = proposal_repo.create_proposal(
        db, text, json.dumps(parsed, ensure_ascii=False), None, proposal_status,
        owner_id=get_current_owner_id(), thread_id=thread.id, request_id=data.request_id,
        idempotency_key=data.idempotency_key, expires_at=expires_at,
        resolved_absolute_dates=json.dumps(parsed["resolved_absolute_dates"], ensure_ascii=False),
        data_version=1, authority_snapshot_json=canonical_json(authority), updated_at=created_at,
    )
    pending = PendingAction(
        tenant_id=get_current_tenant_id(), thread_id=thread.id, proposal_id=proposal.id,
        status="pending", expires_at=expires_at, created_at=created_at, updated_at=created_at,
    )
    db.add(pending)
    db.flush()
    assistant = Message(
        tenant_id=get_current_tenant_id(), session_id=session.id, role="assistant",
        content=("请先确认产品身份；确认后会与其他候选合并为一张最终确认卡。"
                 if parsed.get("resolution_required") else
                 "已整理为一张统一确认卡，确认前不会写入账本。"),
        message_type="block", created_at=created_at,
    )
    db.add(assistant)
    db.flush()
    card = proposal_dict(proposal)
    db.add(MessageBlock(
        tenant_id=get_current_tenant_id(), message_id=assistant.id,
        block_type="product_match_card" if parsed.get("resolution_required") else "confirm_card",
        payload_json=json.dumps(card, ensure_ascii=False), state=proposal_status, data_version=1,
        proposal_id=proposal.id, created_at=created_at,
    ))
    _save_mentions(db, assistant.id, mentions)
    _update_summary(db, session, mentions, pending.id)
    thread.last_active_at = created_at
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        duplicate = proposal_repo.get_by_idempotency_key(db, data.idempotency_key)
        if duplicate is None:
            raise
        return {"status": duplicate.status, "idempotent_replay": True, "proposal": proposal_dict(duplicate)}
    return {
        "status": proposal_status, "idempotent_replay": False,
        "proposal": proposal_dict(proposal), "product_match": parsed.get("product_match"),
    }


def _handle_pending_voice_command(db: Session, data, now: datetime | None = None) -> dict | None:
    """转写文本与手动按钮共用同一 Proposal 服务，不另开语音写接口。"""
    text = data.text.strip()
    if not re.search(r"^(确认|取消|选择?第?[一二三123]个|作为新产品|新增这个产品|去掉.+)$", text):
        return None
    items = pending_actions(db, now=now)["items"]
    matching_resolution = next(
        (
            item["proposal"] for item in items
            if item["proposal"].get("resolution_idempotency_key") == data.idempotency_key
        ),
        None,
    )
    if matching_resolution is not None:
        return {
            "status": matching_resolution["status"], "idempotent_replay": True,
            "proposal": matching_resolution,
        }
    current = next(
        (item["proposal"] for item in items if item["proposal"]["status"] in {"resolving", "pending"}),
        None,
    )
    if current is None:
        return None

    if current["status"] == "resolving":
        from app.application import stage4_entity_service
        from app.schemas.conversation import ProductResolutionChoiceRequest

        match = current.get("product_match") or {}
        if text in {"作为新产品", "新增这个产品"}:
            recognized = match.get("recognized") or {}
            request = ProductResolutionChoiceRequest(
                data_version=current["data_version"], idempotency_key=data.idempotency_key,
                create_new=True, canonical_name=recognized.get("name"),
                brand=recognized.get("brand"), specification=recognized.get("specification"),
            )
        else:
            mapping = {"一": 0, "1": 0, "二": 1, "2": 1, "三": 2, "3": 2}
            token = re.search(r"[一二三123]", text)
            index = mapping.get(token.group(0), 0) if token else 0
            candidates = match.get("candidates") or []
            if index >= len(candidates):
                raise DomainError("产品候选没有这一项，请重新选择")
            request = ProductResolutionChoiceRequest(
                data_version=current["data_version"], idempotency_key=data.idempotency_key,
                product_id=candidates[index]["id"],
            )
        return stage4_entity_service.resolve_proposal_product(db, current["id"], request)

    from app.application import stage3_proposal_service
    if text == "确认":
        from app.schemas.conversation import ProposalConfirmRequest

        result = stage3_proposal_service.confirm(
            db, current["id"], ProposalConfirmRequest(
                idempotency_key=data.idempotency_key, device_id=data.device_id,
                data_version=current["data_version"],
            ), now=now,
        )
        return {"status": "confirmed", "proposal": current, "result": result}
    if text == "取消":
        from app.schemas.conversation import ProposalCancelRequest

        result = stage3_proposal_service.cancel(
            db, current["id"], ProposalCancelRequest(
                idempotency_key=data.idempotency_key, device_id=data.device_id,
            ), now=now,
        )
        return {"status": "cancelled", "proposal": current, "result": result}
    if text.startswith("去掉"):
        keyword = text[2:].strip()
        indexes = [
            index for index, action in enumerate(current.get("actions") or [])
            if action.get("type") == "upsert_customer_fact" and (
                action.get("display_value", "") in keyword
                or keyword in action.get("display_value", "")
                or ("敏感" in keyword and action.get("sensitivity_level") == "sensitive")
            )
        ]
        if not indexes:
            raise DomainError("没有找到要移除的客户事实候选")
        from app.schemas.conversation import ProposalEditRequest

        return stage3_proposal_service.edit(
            db, current["id"], ProposalEditRequest(
                idempotency_key=data.idempotency_key, data_version=current["data_version"],
                remove_action_indexes=indexes,
            ), now=now,
        )
    return None


def pending_actions(db: Session, now: datetime | None = None) -> dict:
    thread = get_or_create_thread(db)
    current = _utc_naive(now)
    rows = conversation_repo.list_pending(db, thread.id)
    changed = False
    result = []
    for pending in rows:
        proposal = proposal_repo.get_proposal(db, pending.proposal_id) if pending.proposal_id else None
        if pending.status == "pending" and pending.expires_at and pending.expires_at <= current:
            pending.status = "expired"
            pending.updated_at = current
            pending.resolved_at = current
            if proposal and proposal.status in {"pending", "resolving"}:
                proposal.status = "expired"
                proposal.updated_at = current
            changed = True
        if proposal:
            result.append({
                "id": pending.id, "status": pending.status,
                "read_at": pending.read_at.isoformat() if pending.read_at else None,
                "proposal": proposal_dict(proposal),
            })
    if changed:
        db.commit()
    return {"thread_id": thread.id, "items": result}


def assemble_context(db: Session, current_input: str, max_recent: int = 12) -> dict:
    thread = get_or_create_thread(db)
    session = get_or_create_session(db, thread)
    pending = pending_actions(db)["items"]
    terms = [token for token in re.split(r"\s+|[，。；,.]", current_input) if len(token) >= 2]
    recent = conversation_repo.recent_relevant_messages(db, thread.id, terms, min(max_recent, 12))
    summary = conversation_repo.get_summary(db, session.id) or conversation_repo.get_latest_summary(db, thread.id)
    authority = []
    for item in pending[:5]:
        proposal = proposal_repo.get_proposal(db, item["proposal"]["id"])
        authority.append(_load_json(proposal.authority_snapshot_json, {}))
    return {
        "current_input": current_input,
        "pending_actions": pending,
        "recent_relevant_messages": [
            {"id": m.id, "role": m.role, "content": m.content} for m in reversed(recent)
        ],
        "summary": {
            "topics": _load_json(summary.topics, []) if summary else [],
            "entity_ids": _load_json(summary.entity_ids, []) if summary else [],
            "pending_ids": _load_json(summary.pending_ids, []) if summary else [],
        },
        "latest_authoritative_objects": authority,
        "full_history_sent": False,
        "recent_message_limit": min(max_recent, 12),
    }
