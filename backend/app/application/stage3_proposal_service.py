"""统一 Proposal 的过期、编辑、强幂等、并发冲突和原子确认。"""
import json
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from app.application import confirmation_service
from app.application.conversation_service import (
    _local_date,
    _load_json,
    _utc_naive,
    get_or_create_thread,
    proposal_dict,
)
from app.application.stage3_authority import build_authority_snapshot, canonical_json, snapshot_diff
from app.core.tenant import get_current_owner_id, get_current_tenant_id
from app.domain.errors import ConflictError, DomainError, NotFoundError
from app.infrastructure.models import AgentProposal, Message, MessageBlock, PendingAction
from app.repositories import conversations as conversation_repo
from app.repositories import proposals as proposal_repo
from app.schemas.agent import ConfirmRequest


def _proposal(db: Session, proposal_id: int) -> AgentProposal:
    proposal = proposal_repo.get_proposal(db, proposal_id)
    if proposal is None or proposal.owner_id != get_current_owner_id():
        raise NotFoundError("确认卡不存在")
    return proposal


def _parsed(proposal: AgentProposal) -> dict:
    value = _load_json(proposal.parsed_json, {})
    if not value.get("actions"):
        raise DomainError("确认卡缺少可执行操作")
    return value


def _set_pending_state(db: Session, proposal_id: int, status: str, now: datetime) -> None:
    pending = conversation_repo.get_pending_for_proposal(db, proposal_id)
    if pending:
        pending.status = status
        pending.updated_at = now
        if status in {"completed", "cancelled", "expired", "stale", "regenerated"}:
            pending.resolved_at = now


def _set_block_state(db: Session, proposal: AgentProposal, state: str) -> None:
    block = conversation_repo.get_block_for_proposal(db, proposal.id)
    if block:
        block.state = state
        block.data_version = proposal.data_version
        block.payload_json = json.dumps(proposal_dict(proposal), ensure_ascii=False)


def _receipt(
    db: Session,
    proposal: AgentProposal,
    *,
    status: str,
    title: str,
    detail: str,
    result=None,
    request_id: str | None = None,
    now: datetime | None = None,
) -> dict:
    current = now or _utc_naive()
    if request_id and conversation_repo.get_message_by_request(db, request_id):
        return {"status": status, "title": title, "detail": detail, "result": result}
    thread = get_or_create_thread(db)
    session = conversation_repo.get_session(db, thread.id, _local_date(current.replace(tzinfo=timezone.utc)))
    if session is None:
        from app.infrastructure.models import ConversationSession

        session = ConversationSession(
            tenant_id=get_current_tenant_id(), thread_id=thread.id,
            session_date=_local_date(current.replace(tzinfo=timezone.utc)),
            timezone="Asia/Shanghai", started_at=current,
        )
        db.add(session)
        db.flush()
    payload = {"status": status, "title": title, "detail": detail, "result": result}
    message = Message(
        tenant_id=get_current_tenant_id(), session_id=session.id, role="assistant",
        content=title, message_type="block", request_id=request_id, created_at=current,
    )
    db.add(message)
    db.flush()
    db.add(MessageBlock(
        tenant_id=get_current_tenant_id(), message_id=message.id, block_type="receipt_card",
        payload_json=json.dumps(payload, ensure_ascii=False), state=status,
        data_version=proposal.data_version, proposal_id=proposal.id, created_at=current,
    ))
    return payload


def _mark_expired(db: Session, proposal: AgentProposal, now: datetime) -> None:
    proposal.status = "expired"
    proposal.updated_at = now
    _set_pending_state(db, proposal.id, "expired", now)
    _set_block_state(db, proposal, "expired")


def _conflict_payload(proposal: AgentProposal, kind: str, **extra) -> dict:
    return {
        "status": kind,
        "proposal_id": proposal.id,
        "proposal": proposal_dict(proposal),
        **extra,
    }


def confirm(db: Session, proposal_id: int, data, now: datetime | None = None) -> dict:
    proposal = _proposal(db, proposal_id)
    current = _utc_naive(now)

    if proposal.status == "confirmed":
        result = _load_json(proposal.result_json, {})
        if proposal.confirmation_idempotency_key == data.idempotency_key:
            return {**result, "idempotent_replay": True}
        payload = _conflict_payload(
            proposal, "conflict", conflict_type="already_confirmed",
            confirmed_by_device=proposal.confirmed_by_device, original_result=result,
        )
        _receipt(
            db, proposal, status="conflict", title="另一设备已完成确认",
            detail="账本没有重复写入，可刷新查看原处理结果。", result=result,
            request_id=f"conflict-{data.idempotency_key}"[:64], now=current,
        )
        db.commit()
        raise ConflictError("该确认卡已由另一设备处理", payload)

    if proposal.status in {"cancelled", "expired", "stale"}:
        raise ConflictError(
            "该确认卡已失效，请基于当前数据重新生成",
            _conflict_payload(proposal, proposal.status, conflict_type="proposal_not_pending"),
        )
    if proposal.status == "resolving":
        raise ConflictError(
            "请先完成产品匹配，再进行最终确认",
            _conflict_payload(proposal, "resolving", conflict_type="product_resolution_required"),
        )
    if proposal.expires_at and proposal.expires_at <= current:
        _mark_expired(db, proposal, current)
        db.commit()
        raise ConflictError(
            "该确认卡已过期，请重新生成",
            _conflict_payload(proposal, "expired", conflict_type="expired"),
        )
    if proposal.data_version != data.data_version:
        raise ConflictError(
            "确认卡版本已变化，请刷新后重新确认",
            _conflict_payload(proposal, "conflict", conflict_type="data_version"),
        )

    parsed = _parsed(proposal)
    if any(action.get("type") in {"publish_knowledge", "withdraw_knowledge"} for action in parsed["actions"]):
        from app.core.rbac import require_admin

        require_admin()
    before = _load_json(proposal.authority_snapshot_json, {})
    try:
        current_snapshot = build_authority_snapshot(db, parsed)
    except DomainError as exc:
        current_snapshot = {"error": str(exc)}
    differences = snapshot_diff(before, current_snapshot)
    if differences:
        proposal.status = "stale"
        proposal.updated_at = current
        _set_pending_state(db, proposal.id, "stale", current)
        _set_block_state(db, proposal, "stale")
        _receipt(
            db, proposal, status="conflict", title="数据已变化，需要重新确认",
            detail="系统已重新读取当前权威数据，旧确认卡未执行。", result=differences,
            request_id=f"stale-{proposal.id}-{proposal.data_version}", now=current,
        )
        db.commit()
        raise ConflictError(
            "权威数据已变化，旧确认卡禁止执行",
            _conflict_payload(
                proposal, "stale", conflict_type="authority_changed", differences=differences,
                current_authority=current_snapshot,
            ),
        )

    try:
        claimed = proposal_repo.claim_pending(
            db, proposal.id, data.data_version, data.idempotency_key, data.device_id, current
        )
    except OperationalError as exc:
        db.rollback()
        if "locked" not in str(exc).lower():
            raise
        raise ConflictError(
            "另一设备正在确认，请刷新查看处理结果",
            _conflict_payload(proposal, "conflict", conflict_type="concurrent_confirmation"),
        ) from exc
    if not claimed:
        db.rollback()
        latest = _proposal(db, proposal_id)
        if latest.status == "confirmed" and latest.confirmation_idempotency_key == data.idempotency_key:
            return {**_load_json(latest.result_json, {}), "idempotent_replay": True}
        raise ConflictError(
            "确认卡正在或已经由另一设备处理",
            _conflict_payload(latest, "conflict", conflict_type="concurrent_confirmation"),
        )

    try:
        db.refresh(proposal)
        request = ConfirmRequest.model_validate(
            {"customer": parsed.get("customer"), "actions": parsed["actions"]}
        )
        customer = (
            confirmation_service._resolve_customer_confirm(db, request.customer)
            if request.customer is not None else None
        )
        validations = [confirmation_service._validate_action(db, customer, action) for action in request.actions]
        failures = [item for item in validations if not item["ok"]]
        if failures:
            raise DomainError("；".join(item["error"] for item in failures))
        results = [
            confirmation_service._execute_action(db, customer, action, proposal)
            for action in request.actions
        ]
        proposal.status = "confirmed"
        proposal.confirmed_at = current
        proposal.updated_at = current
        response = {
            "id": proposal.id,
            "status": "confirmed",
            "customer": (
                {"id": customer.id, "display_name": customer.display_name} if customer else None
            ),
            "results": results,
            "idempotent_replay": False,
        }
        proposal.result_json = json.dumps(response, ensure_ascii=False)
        _set_pending_state(db, proposal.id, "completed", current)
        _set_block_state(db, proposal, "confirmed")
        _receipt(
            db, proposal, status="success", title="已确认并写入",
            detail="全部操作已在同一个数据库事务中完成。",
            result=[item.get("message") for item in results],
            request_id=f"confirmed-{data.idempotency_key}"[:64], now=current,
        )
        db.commit()
        return response
    except Exception:
        db.rollback()
        raise


def cancel(db: Session, proposal_id: int, data, now: datetime | None = None) -> dict:
    proposal = _proposal(db, proposal_id)
    current = _utc_naive(now)
    if proposal.status == "cancelled":
        return {"id": proposal.id, "status": "cancelled", "idempotent_replay": True}
    if proposal.status != "pending":
        raise ConflictError(
            "该确认卡已处理，不能取消",
            _conflict_payload(proposal, "conflict", conflict_type="already_resolved"),
        )
    proposal.status = "cancelled"
    proposal.updated_at = current
    _set_pending_state(db, proposal.id, "cancelled", current)
    _set_block_state(db, proposal, "cancelled")
    _receipt(
        db, proposal, status="cancelled", title="已取消",
        detail="未写入任何账本数据。", request_id=f"cancel-{data.idempotency_key}"[:64], now=current,
    )
    db.commit()
    return {"id": proposal.id, "status": "cancelled", "idempotent_replay": False}


def edit(db: Session, proposal_id: int, data, now: datetime | None = None) -> dict:
    proposal = _proposal(db, proposal_id)
    current = _utc_naive(now)
    if proposal.status != "pending" or proposal.data_version != data.data_version:
        raise ConflictError(
            "确认卡状态或版本已变化，请刷新",
            _conflict_payload(proposal, "conflict", conflict_type="edit_version"),
        )
    if proposal.expires_at and proposal.expires_at <= current:
        _mark_expired(db, proposal, current)
        db.commit()
        raise ConflictError("该确认卡已过期", _conflict_payload(proposal, "expired"))
    parsed = _parsed(proposal)
    if data.occurred_on:
        try:
            fixed = date.fromisoformat(data.occurred_on).isoformat()
        except ValueError as exc:
            raise DomainError("日期格式必须为 YYYY-MM-DD") from exc
        for action in parsed["actions"]:
            action["occurred_on"] = fixed
        dates = _load_json(proposal.resolved_absolute_dates, {})
        dates["occurred_on"] = {
            "expression": "店主修改",
            "date": fixed,
            "timezone": "Asia/Shanghai",
            "resolved_at": current.replace(tzinfo=timezone.utc).isoformat(),
        }
        parsed["resolved_absolute_dates"] = dates
        proposal.resolved_absolute_dates = json.dumps(dates, ensure_ascii=False)
    for key, quantity in data.quantities.items():
        try:
            index = int(key)
            if quantity < 1:
                raise ValueError
            parsed["actions"][index]["quantity"] = quantity
        except (ValueError, IndexError) as exc:
            raise DomainError("修改数量无效") from exc
    indexes = sorted(set(data.remove_action_indexes), reverse=True)
    for index in indexes:
        if index < 0 or index >= len(parsed["actions"]):
            raise DomainError("要移除的候选项不存在")
        parsed["actions"].pop(index)
    if not parsed["actions"]:
        raise DomainError("确认卡至少需要保留一项操作")
    parsed["changes_summary"] = "；".join(_action_summary(action) for action in parsed["actions"])
    proposal.parsed_json = json.dumps(parsed, ensure_ascii=False)
    proposal.data_version += 1
    proposal.updated_at = current
    proposal.authority_snapshot_json = canonical_json(build_authority_snapshot(db, parsed))
    _set_block_state(db, proposal, "pending")
    db.commit()
    return {"status": "pending", "proposal": proposal_dict(proposal)}


def _action_summary(action: dict) -> str:
    action_type = action.get("type")
    if action_type == "upsert_customer_fact":
        return f"客户事实：{action.get('display_value', '未填写')}"
    if action_type == "delete_customer_fact":
        return f"撤销客户事实：{action.get('display_value', '未填写')}"
    if action_type == "record_product_purchase":
        return f"购买{action.get('canonical_name') or action.get('product_name', '产品')} {action.get('quantity', 1)}件"
    if action_type == "create_product":
        return f"新增产品草稿：{action.get('canonical_name', '未填写')}"
    if action_type == "merge_product":
        return "合并重复产品"
    if action_type == "publish_knowledge":
        return f"发布{action.get('entity_type')}知识：{action.get('title', '未填写')}"
    if action_type == "withdraw_knowledge":
        return f"撤回{action.get('entity_type')}知识"
    return f"{action.get('service_name', action_type)} {action.get('quantity', 1)} 次"


def regenerate(db: Session, proposal_id: int, data, now: datetime | None = None) -> dict:
    old = _proposal(db, proposal_id)
    if old.status not in {"expired", "stale"}:
        raise ConflictError(
            "只有过期或数据已变化的确认卡才能重新生成",
            _conflict_payload(old, "conflict", conflict_type="not_regenerable"),
        )
    duplicate = proposal_repo.get_by_idempotency_key(db, data.idempotency_key)
    if duplicate:
        return {"status": duplicate.status, "proposal": proposal_dict(duplicate), "idempotent_replay": True}
    current = _utc_naive(now)
    parsed = _parsed(old)
    snapshot = build_authority_snapshot(db, parsed)
    new = proposal_repo.create_proposal(
        db, old.original_input, json.dumps(parsed, ensure_ascii=False), old.prompt_version, "pending",
        owner_id=old.owner_id, thread_id=old.thread_id, request_id=data.request_id,
        idempotency_key=data.idempotency_key, expires_at=current + timedelta(hours=24),
        resolved_absolute_dates=old.resolved_absolute_dates, data_version=old.data_version + 1,
        authority_snapshot_json=canonical_json(snapshot), updated_at=current,
    )
    db.flush()
    pending = PendingAction(
        tenant_id=get_current_tenant_id(), thread_id=old.thread_id, proposal_id=new.id,
        status="pending", expires_at=new.expires_at, created_at=current, updated_at=current,
    )
    db.add(pending)
    _set_pending_state(db, old.id, "regenerated", current)
    _set_block_state(db, old, "regenerated")
    thread = get_or_create_thread(db)
    session = conversation_repo.get_session(db, thread.id, _local_date(current.replace(tzinfo=timezone.utc)))
    if session is None:
        from app.infrastructure.models import ConversationSession

        session = ConversationSession(
            tenant_id=get_current_tenant_id(), thread_id=thread.id,
            session_date=_local_date(current.replace(tzinfo=timezone.utc)),
            timezone="Asia/Shanghai", started_at=current,
        )
        db.add(session)
        db.flush()
    message = Message(
        tenant_id=get_current_tenant_id(), session_id=session.id, role="assistant",
        content="已按当前权威数据重新生成确认卡。", message_type="block", created_at=current,
    )
    db.add(message)
    db.flush()
    db.add(MessageBlock(
        tenant_id=get_current_tenant_id(), message_id=message.id, block_type="confirm_card",
        payload_json=json.dumps(proposal_dict(new), ensure_ascii=False), state="pending",
        data_version=new.data_version, proposal_id=new.id, created_at=current,
    ))
    db.commit()
    return {"status": "pending", "proposal": proposal_dict(new), "idempotent_replay": False}
