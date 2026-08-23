"""阶段6：SQL 权威推荐、证据快照、安全话术和店主反馈。

本模块不引用 ChatModel，不联网，也不发送消息。规则候选只能来自当前 tenant
的数据库；RAG 仅通过阶段5 retrieve 读取已确认当前证据。
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.application import rag_service
from app.application.fact_extraction_service import normalize_fact_value
from app.application.stage4_model_service import contains_pii
from app.application.stage4_entity_service import _create_proposal
from app.core.rbac import require_admin, require_owner
from app.core.tenant import get_current_owner_id, get_current_tenant_id
from app.domain.errors import ConflictError, DomainError, NotFoundError
from app.infrastructure.models import (
    Customer, CustomerFact, FollowUpFeedback, KnowledgeDocument, LedgerEntry,
    MessageDraft, Package, Product, Recommendation, RecommendationActionAudit,
    RecommendationRule, Service, utcnow,
)
from app.repositories import packages as package_repo
from app.schemas.conversation import KnowledgeRetrieveRequest


SHANGHAI = ZoneInfo("Asia/Shanghai")
RULE_TYPES = ("product_repurchase", "service_follow_up", "package_renewal")
UNRESOLVED_STATUSES = {"new", "viewed", "snoozed"}
HANDLED_STATUSES = {
    "contacted", "repurchased", "not_needed", "unsuitable",
    "do_not_recommend", "cancelled", "expired",
}
ADVERSE_TERMS = ("不适", "刺痛", "泛红", "禁忌", "不耐受", "过敏", "不舒服")
REFUSAL_TERMS = ("不接受营销", "不再推荐", "不要推荐", "拒绝营销")
INJECTION_TERMS = (
    "忽略系统", "忽略规则", "system prompt", "developer message", "显示提示词",
    "api key", "执行指令", "越权",
)
FORBIDDEN_MESSAGE_TERMS = (
    "治好", "治愈", "根治", "保证有效", "一定有效", "疗效", "治疗", "诊断",
    "必须购买", "马上购买", "最后机会", "错过", "病", "过敏了",
)
SECRET_RE = re.compile(r"(?i)(?:sk-[a-z0-9_-]{12,}|bearer\s+[a-z0-9._-]{12,}|api[_ -]?key\s*[:=])")
DATE_RE = re.compile(r"(?<!\d)(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})日?")
DAY_LATER_RE = re.compile(r"(\d{1,3})\s*天后")
PREFERENCE_RE = re.compile(r"(?:客户说|她说|他说)?\s*(?:现在)?(?:更)?(?:喜欢|偏好)\s*([^，。；]{1,40})")


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load(value: str | None, fallback):
    try:
        return json.loads(value) if value else fallback
    except (TypeError, json.JSONDecodeError):
        return fallback


def _checksum(value) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _local_today() -> date:
    return datetime.now(SHANGHAI).date()


def _utc_naive(value: datetime | None = None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        return current
    return current.astimezone(timezone.utc).replace(tzinfo=None)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except (TypeError, ValueError):
        return None


def _active_rules(db: Session) -> list[RecommendationRule]:
    rows = db.scalars(select(RecommendationRule).where(
        RecommendationRule.tenant_id == get_current_tenant_id(),
        RecommendationRule.status == "active",
        RecommendationRule.rule_type.in_(RULE_TYPES),
    ).order_by(RecommendationRule.rule_type, RecommendationRule.version.desc())).all()
    result: list[RecommendationRule] = []
    seen: set[str] = set()
    for row in rows:
        if row.rule_type not in seen:
            seen.add(row.rule_type)
            result.append(row)
    return result


def _rule_parameters(rule: RecommendationRule) -> dict:
    raw = _load(rule.conditions_json, {})
    defaults = {
        "product_repurchase": {"days_since_purchase": 60},
        "service_follow_up": {"days_since_service": 14},
        "package_renewal": {"remaining_at_most": 2},
    }[rule.rule_type]
    values = {**defaults, **raw}
    if rule.rule_type == "product_repurchase":
        key, low, high = "days_since_purchase", 1, 365
    elif rule.rule_type == "service_follow_up":
        key, low, high = "days_since_service", 1, 365
    else:
        key, low, high = "remaining_at_most", 0, 20
    value = values.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise DomainError(f"推荐规则 {rule.id} 参数无效")
    return {key: value}


def list_rules_readonly(db: Session) -> list[dict]:
    require_admin()
    return [{
        "id": row.id, "rule_type": row.rule_type, "version": row.version,
        "policy_version": row.policy_version, "cooldown_days": row.cooldown_days,
        "priority": row.priority, "status": row.status,
        "conditions": _load(row.conditions_json, {}),
        "hard_exclusions": _load(row.hard_exclusions_json, []),
        "score_config": _load(row.score_config_json, {}),
        "readonly": True,
    } for row in _active_rules(db)]


def _current_knowledge(db: Session, entity_type: str, entity_id: int) -> KnowledgeDocument | None:
    return db.scalar(select(KnowledgeDocument).where(
        KnowledgeDocument.tenant_id == get_current_tenant_id(),
        KnowledgeDocument.entity_type == entity_type,
        KnowledgeDocument.entity_id == entity_id,
        KnowledgeDocument.confirmed.is_(True), KnowledgeDocument.active.is_(True),
        KnowledgeDocument.status == "published", KnowledgeDocument.withdrawn_at.is_(None),
    ).order_by(KnowledgeDocument.knowledge_version.desc()).limit(1))


def _confirmed_facts(db: Session, customer_id: int) -> list[CustomerFact]:
    return list(db.scalars(select(CustomerFact).where(
        CustomerFact.tenant_id == get_current_tenant_id(),
        CustomerFact.customer_id == customer_id,
        CustomerFact.confirmation_status == "confirmed",
        CustomerFact.valid_to.is_(None), CustomerFact.deleted_at.is_(None),
    )).all())


def _has_fact_exclusion(db: Session, customer_id: int) -> str | None:
    for fact in _confirmed_facts(db, customer_id):
        value = f"{fact.fact_type} {fact.display_value} {fact.normalized_value or ''}".lower()
        if any(term in value for term in REFUSAL_TERMS):
            return "confirmed_marketing_refusal"
        if any(term in value for term in ADVERSE_TERMS):
            return "confirmed_unresolved_adverse_fact"
    return None


def _feedback_refusal_active(db: Session, customer_id: int, trigger: str, subject_id: int) -> bool:
    rows = db.scalars(select(FollowUpFeedback).where(
        FollowUpFeedback.tenant_id == get_current_tenant_id(),
        FollowUpFeedback.customer_id == customer_id,
        FollowUpFeedback.action_type.in_(("do_not_recommend", "allow_recommendation")),
    ).order_by(FollowUpFeedback.created_at.desc(), FollowUpFeedback.id.desc())).all()
    for row in rows:
        context = _load(row.anonymous_context_json, {})
        if context.get("trigger_type") not in (None, trigger):
            continue
        if context.get("subject_id") not in (None, subject_id):
            continue
        return row.action_type == "do_not_recommend"
    return False


def _existing_guard(
    db: Session, *, customer_id: int, trigger: str, subject_type: str,
    subject_id: int, rule: RecommendationRule, generation_key: str,
    now: datetime,
) -> str | None:
    rows = db.scalars(select(Recommendation).where(
        Recommendation.tenant_id == get_current_tenant_id(),
        Recommendation.customer_id == customer_id,
        Recommendation.trigger_type == trigger,
        Recommendation.subject_type == subject_type,
        Recommendation.subject_id == subject_id,
        Recommendation.generation_key != generation_key,
    ).order_by(Recommendation.created_at.desc())).all()
    cutoff = now - timedelta(days=max(0, rule.cooldown_days))
    for row in rows:
        latest_feedback = db.scalar(select(FollowUpFeedback.action_type).where(
            FollowUpFeedback.tenant_id == get_current_tenant_id(),
            FollowUpFeedback.recommendation_id == row.id,
        ).order_by(FollowUpFeedback.created_at.desc(), FollowUpFeedback.id.desc()).limit(1))
        if latest_feedback == "allow_recommendation":
            continue
        if row.status in UNRESOLVED_STATUSES:
            return "unresolved_duplicate"
        if row.contacted_at and row.contacted_at >= cutoff:
            return "contact_cooldown"
        if row.updated_at and row.updated_at >= cutoff and row.status in {"not_needed", "unsuitable", "cancelled"}:
            return "handled_cooldown"
    return None


def _rag_snapshot(db: Session, *, entity_type: str, entity_id: int, query: str) -> tuple[list[dict], bool, str | None]:
    try:
        result = rag_service.retrieve(db, KnowledgeRetrieveRequest(
            query=query, entity_type=entity_type, entity_id=entity_id, limit=5,
        ))
        evidence = result.get("evidence") or []
        valid = [item for item in evidence if (
            item.get("entity_type") == entity_type and item.get("entity_id") == entity_id
        )]
        if valid:
            degraded = result.get("status") == "fallback"
            return valid, degraded, "rag_index_fallback" if degraded else None
        return [], True, "rag_knowledge_insufficient"
    except Exception:
        return [], True, "rag_unavailable"


def _hard_gate(
    db: Session, *, customer: Customer, entity_type: str, entity_id: int,
    trigger: str, rule: RecommendationRule, generation_key: str, now: datetime,
) -> str | None:
    if customer.deleted_at is not None:
        return "customer_deleted"
    fact_reason = _has_fact_exclusion(db, customer.id)
    if fact_reason:
        return fact_reason
    if _feedback_refusal_active(db, customer.id, trigger, entity_id):
        return "feedback_do_not_recommend"
    if _current_knowledge(db, entity_type, entity_id) is None:
        return "current_confirmed_knowledge_missing"
    return _existing_guard(
        db, customer_id=customer.id, trigger=trigger, subject_type=entity_type,
        subject_id=entity_id, rule=rule, generation_key=generation_key, now=now,
    )


def _score(rule: RecommendationRule, *, overdue_days: int, evidence_count: int, remaining: int | None = None) -> tuple[float, dict]:
    config = _load(rule.score_config_json, {})
    base = float(config.get("base", 50))
    overdue_weight = float(config.get("overdue_per_day", 0.5))
    evidence_weight = float(config.get("evidence", 8))
    balance_weight = float(config.get("low_balance", 12)) if remaining is not None and remaining <= 2 else 0.0
    for value in (base, overdue_weight, evidence_weight, balance_weight):
        if not -100 <= value <= 100:
            raise DomainError(f"推荐规则 {rule.id} 评分参数无效")
    breakdown = {
        "base": round(base, 4),
        "overdue": round(min(max(overdue_days, 0) * overdue_weight, 30), 4),
        "structured_evidence": round(evidence_weight if evidence_count else 0, 4),
        "low_balance": round(balance_weight, 4),
        "rule_priority": rule.priority,
    }
    return round(sum(breakdown.values()), 4), breakdown


def _safe_message(kind: str, *, customer: str, subject: str, remaining: int | None = None, variant: str = "standard") -> str:
    def safe_label(value: str, fallback: str) -> str:
        cleaned = re.sub(r"<[^>]{0,500}>", "", str(value or "")).strip()
        lowered = cleaned.lower()
        if (
            not cleaned or len(cleaned) > 80 or contains_pii(cleaned) or SECRET_RE.search(cleaned)
            or any(term in lowered for term in INJECTION_TERMS)
        ):
            return fallback
        return cleaned

    customer = safe_label(customer, "您好")
    subject = safe_label(subject, "相关产品" if kind == "product_repurchase" else "相关服务")
    if kind == "product_repurchase":
        standard = f"{customer}，想问问您最近{subject}用着还顺手吗？如果快用完了，需要时再和我说。"
        shorter = f"{customer}，最近{subject}用着还顺手吗？需要时和我说就好。"
        no_purchase = f"{customer}，想问问您最近{subject}用着感觉怎么样？有需要时再联系我就好。"
    elif kind == "service_follow_up":
        standard = f"{customer}，最近感觉怎么样？您这边{subject}还有{remaining}次，如果想安排时间，我再帮您看看。"
        shorter = f"{customer}，最近怎么样？{subject}还有{remaining}次，需要安排时和我说。"
        no_purchase = f"{customer}，想问问最近感觉怎么样？如果想安排{subject}，再联系我就好。"
    else:
        standard = f"{customer}，想问问最近{subject}的体验怎么样？现有次数不多了，您有需要时我们再聊。"
        shorter = f"{customer}，最近{subject}体验怎么样？有需要时再聊。"
        no_purchase = f"{customer}，想问问最近体验怎么样？需要安排时再联系我就好。"
    value = {"standard": standard, "shorter": shorter, "no_purchase": no_purchase}[variant]
    lowered = value.lower()
    if len(value) > 180 or SECRET_RE.search(value) or any(term in lowered for term in INJECTION_TERMS + FORBIDDEN_MESSAGE_TERMS):
        return f"{customer}，最近感觉怎么样？有需要时再联系我就好。"
    return value


def _candidate_base(
    *, customer: Customer, rule: RecommendationRule, target_date: date,
    entity_type: str, entity_id: int, trigger: str,
) -> tuple[str, str]:
    raw = f"{get_current_owner_id()}|{target_date.isoformat()}|{rule.id}|{rule.version}|{customer.id}|{trigger}|{entity_type}|{entity_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:128], raw


def _product_candidates(db: Session, rule: RecommendationRule, target_date: date, now: datetime) -> tuple[list[dict], list[dict]]:
    threshold = _rule_parameters(rule)["days_since_purchase"]
    rows = db.execute(select(Customer, Product, LedgerEntry).join(
        LedgerEntry, LedgerEntry.customer_id == Customer.id,
    ).join(Product, Product.id == LedgerEntry.product_id).where(
        Customer.tenant_id == get_current_tenant_id(), Customer.deleted_at.is_(None),
        Product.tenant_id == get_current_tenant_id(), Product.deleted_at.is_(None),
        Product.lifecycle_status == "active", Product.merged_into_id.is_(None),
        LedgerEntry.tenant_id == get_current_tenant_id(),
        LedgerEntry.entry_type == "product_purchase", LedgerEntry.deleted_at.is_(None),
    ).order_by(Customer.id, Product.id, LedgerEntry.occurred_on.desc(), LedgerEntry.id.desc())).all()
    latest: dict[tuple[int, int], tuple[Customer, Product, LedgerEntry]] = {}
    for customer, product, entry in rows:
        latest.setdefault((customer.id, product.id), (customer, product, entry))
    candidates, excluded = [], []
    for customer, product, entry in latest.values():
        occurred = _parse_date(entry.occurred_on)
        if occurred is None or entry.quantity <= 0:
            excluded.append({"customer_id": customer.id, "reason": "invalid_purchase_evidence"})
            continue
        elapsed = (target_date - occurred).days
        if elapsed < threshold:
            continue
        generation_key, _ = _candidate_base(
            customer=customer, rule=rule, target_date=target_date,
            entity_type="product", entity_id=product.id, trigger=rule.rule_type,
        )
        gate = _hard_gate(
            db, customer=customer, entity_type="product", entity_id=product.id,
            trigger=rule.rule_type, rule=rule, generation_key=generation_key, now=now,
        )
        if gate:
            excluded.append({"customer_id": customer.id, "subject_id": product.id, "reason": gate})
            continue
        rag, degraded, degraded_reason = _rag_snapshot(
            db, entity_type="product", entity_id=product.id, query=product.canonical_name,
        )
        structured = [{
            "kind": "transaction", "entry_id": entry.id, "occurred_on": occurred.isoformat(),
            "quantity": entry.quantity, "source": "tenant_sql",
        }]
        score, breakdown = _score(rule, overdue_days=elapsed - threshold, evidence_count=len(structured))
        candidates.append({
            "generation_key": generation_key, "customer": customer, "entity_type": "product",
            "entity_id": product.id, "subject_name": product.canonical_name, "trigger": rule.rule_type,
            "score": score, "breakdown": breakdown,
            "reason": f"距最近一次购买已 {elapsed} 天，达到规则 {threshold} 天",
            "suggested_action": "先询问近期使用感受，再按客户需要回应",
            "evidence": structured + rag, "knowledge_versions": [
                {"document_id": item["document_id"], "knowledge_version": item["knowledge_version"]} for item in rag
            ], "degraded": degraded, "degraded_reason": degraded_reason,
            "remaining": None,
        })
    return candidates, excluded


def _service_rows(db: Session):
    packages = db.execute(select(Customer, Service, Package).join(
        Package, Package.customer_id == Customer.id,
    ).join(Service, Service.id == Package.service_id).where(
        Customer.tenant_id == get_current_tenant_id(), Customer.deleted_at.is_(None),
        Package.tenant_id == get_current_tenant_id(), Package.deleted_at.is_(None), Package.status == "active",
        Service.tenant_id == get_current_tenant_id(), Service.deleted_at.is_(None), Service.status == "active",
    )).all()
    used = package_repo.compute_used_counts(db, [row[2] for row in packages])
    return packages, used


def _last_consumption(db: Session, customer_id: int, service_id: int) -> LedgerEntry | None:
    return db.scalar(select(LedgerEntry).where(
        LedgerEntry.tenant_id == get_current_tenant_id(),
        LedgerEntry.customer_id == customer_id, LedgerEntry.service_id == service_id,
        LedgerEntry.entry_type.in_(("package_consumption", "one_time_service")),
        LedgerEntry.deleted_at.is_(None),
    ).order_by(LedgerEntry.occurred_on.desc(), LedgerEntry.id.desc()).limit(1))


def _service_candidates(db: Session, rule: RecommendationRule, target_date: date, now: datetime) -> tuple[list[dict], list[dict]]:
    threshold = _rule_parameters(rule)["days_since_service"]
    packages, used = _service_rows(db)
    grouped: dict[tuple[int, int], dict] = {}
    excluded, candidates = [], []
    for customer, service, package in packages:
        remaining = package.total_count - used[package.id]
        if remaining < 0:
            excluded.append({"customer_id": customer.id, "subject_id": service.id, "reason": "negative_balance_conflict"})
            continue
        item = grouped.setdefault((customer.id, service.id), {
            "customer": customer, "service": service, "remaining": 0,
        })
        item["remaining"] += remaining
    for item in grouped.values():
        customer, service, remaining = item["customer"], item["service"], item["remaining"]
        if remaining <= 0:
            continue
        entry = _last_consumption(db, customer.id, service.id)
        occurred = _parse_date(entry.occurred_on) if entry else None
        if occurred is None:
            excluded.append({"customer_id": customer.id, "subject_id": service.id, "reason": "service_date_insufficient"})
            continue
        elapsed = (target_date - occurred).days
        if elapsed < threshold:
            continue
        generation_key, _ = _candidate_base(
            customer=customer, rule=rule, target_date=target_date,
            entity_type="service", entity_id=service.id, trigger=rule.rule_type,
        )
        gate = _hard_gate(
            db, customer=customer, entity_type="service", entity_id=service.id,
            trigger=rule.rule_type, rule=rule, generation_key=generation_key, now=now,
        )
        if gate:
            excluded.append({"customer_id": customer.id, "subject_id": service.id, "reason": gate})
            continue
        rag, degraded, degraded_reason = _rag_snapshot(
            db, entity_type="service", entity_id=service.id, query=service.name,
        )
        structured = [{
            "kind": "package_balance", "remaining_count": remaining,
            "last_consumed_at": occurred.isoformat(), "ledger_entry_id": entry.id,
            "source": "tenant_sql",
        }]
        score, breakdown = _score(
            rule, overdue_days=elapsed - threshold, evidence_count=len(structured), remaining=remaining,
        )
        candidates.append({
            "generation_key": generation_key, "customer": customer, "entity_type": "service",
            "entity_id": service.id, "subject_name": service.name, "trigger": rule.rule_type,
            "score": score, "breakdown": breakdown,
            "reason": f"距上次服务已 {elapsed} 天，当前权威余量 {remaining} 次",
            "suggested_action": "先关心近况，再询问是否需要安排时间",
            "evidence": structured + rag, "knowledge_versions": [
                {"document_id": value["document_id"], "knowledge_version": value["knowledge_version"]} for value in rag
            ], "degraded": degraded, "degraded_reason": degraded_reason,
            "remaining": remaining,
        })
    return candidates, excluded


def _renewal_candidates(db: Session, rule: RecommendationRule, target_date: date, now: datetime) -> tuple[list[dict], list[dict]]:
    maximum = _rule_parameters(rule)["remaining_at_most"]
    packages, used = _service_rows(db)
    candidates, excluded = [], []
    for customer, service, package in packages:
        remaining = package.total_count - used[package.id]
        if remaining < 0:
            excluded.append({"customer_id": customer.id, "subject_id": service.id, "reason": "negative_balance_conflict"})
            continue
        if remaining > maximum:
            continue
        last = _last_consumption(db, customer.id, service.id)
        occurred = _parse_date(last.occurred_on) if last else _parse_date(package.purchased_on)
        if occurred is None:
            excluded.append({"customer_id": customer.id, "subject_id": service.id, "reason": "renewal_date_insufficient"})
            continue
        generation_key, _ = _candidate_base(
            customer=customer, rule=rule, target_date=target_date,
            entity_type="service", entity_id=service.id, trigger=rule.rule_type,
        )
        gate = _hard_gate(
            db, customer=customer, entity_type="service", entity_id=service.id,
            trigger=rule.rule_type, rule=rule, generation_key=generation_key, now=now,
        )
        if gate:
            excluded.append({"customer_id": customer.id, "subject_id": service.id, "reason": gate})
            continue
        rag, degraded, degraded_reason = _rag_snapshot(
            db, entity_type="service", entity_id=service.id, query=service.name,
        )
        structured = [{
            "kind": "package_balance", "package_id": package.id,
            "total_count": package.total_count, "used_count": used[package.id],
            "remaining_count": remaining, "evidence_date": occurred.isoformat(),
            "source": "tenant_sql",
        }]
        score, breakdown = _score(rule, overdue_days=0, evidence_count=1, remaining=remaining)
        candidates.append({
            "generation_key": generation_key, "customer": customer, "entity_type": "service",
            "entity_id": service.id, "subject_name": service.name, "trigger": rule.rule_type,
            "score": score, "breakdown": breakdown,
            "reason": f"套餐权威余量为 {remaining} 次，达到规则阈值 {maximum} 次",
            "suggested_action": "先询问体验与后续安排，不假设客户一定续购",
            "evidence": structured + rag, "knowledge_versions": [
                {"document_id": value["document_id"], "knowledge_version": value["knowledge_version"]} for value in rag
            ], "degraded": degraded, "degraded_reason": degraded_reason,
            "remaining": remaining,
        })
    return candidates, excluded


def _upsert_candidate(db: Session, candidate: dict, rule: RecommendationRule, target_date: date, now: datetime) -> tuple[Recommendation, bool]:
    tenant_id = get_current_tenant_id()
    owner_id = get_current_owner_id()
    payload = {
        "reason": candidate["reason"], "suggested_action": candidate["suggested_action"],
        "score": candidate["score"], "breakdown": candidate["breakdown"],
        "evidence": candidate["evidence"], "knowledge_versions": candidate["knowledge_versions"],
        "degraded": candidate["degraded"], "degraded_reason": candidate["degraded_reason"],
    }
    checksum = _checksum(payload)
    row = db.scalar(select(Recommendation).where(
        Recommendation.tenant_id == tenant_id,
        Recommendation.generation_key == candidate["generation_key"],
    ))
    created = row is None
    if row is None:
        row = Recommendation(
            tenant_id=tenant_id, owner_id=owner_id, customer_id=candidate["customer"].id,
            subject_type=candidate["entity_type"], subject_id=candidate["entity_id"],
            trigger_type=candidate["trigger"], rule_id=rule.id, rule_version=rule.version,
            policy_version=rule.policy_version, generation_date=target_date.isoformat(),
            generation_key=candidate["generation_key"], status="new", unread_at=now,
            generated_at=now, expires_at=now + timedelta(days=30),
            created_at=now, updated_at=now, data_version=1,
        )
        db.add(row)
        db.flush()
    elif row.content_checksum == checksum:
        return row, False
    else:
        row.data_version += 1
        row.read_at = None
        row.unread_at = now
        row.status = "new"
        row.handled_at = None
        row.updated_at = now
    row.score = candidate["score"]
    row.score_breakdown_json = _json(candidate["breakdown"])
    row.reason = candidate["reason"]
    row.suggested_action = candidate["suggested_action"]
    row.evidence_snapshot = _json(candidate["evidence"])
    row.knowledge_versions = _json(candidate["knowledge_versions"])
    row.degraded = candidate["degraded"]
    row.degraded_reason = candidate["degraded_reason"]
    row.risk_flags_json = _json(["rag_untrusted_data"] + ([candidate["degraded_reason"]] if candidate["degraded_reason"] else []))
    row.content_checksum = checksum
    draft_content = _safe_message(
        candidate["trigger"], customer=candidate["customer"].display_name,
        subject=candidate["subject_name"], remaining=candidate["remaining"],
    )
    draft = db.scalar(select(MessageDraft).where(
        MessageDraft.tenant_id == tenant_id, MessageDraft.recommendation_id == row.id,
        MessageDraft.variant == "standard",
    ))
    if draft is None:
        draft = MessageDraft(
            tenant_id=tenant_id, recommendation_id=row.id, variant="standard",
            content=draft_content, checksum=_checksum({"content": draft_content}),
            data_version=1, created_at=now, updated_at=now,
        )
        db.add(draft)
    elif draft.content != draft_content:
        draft.content = draft_content
        draft.checksum = _checksum({"content": draft_content})
        draft.data_version += 1
        draft.updated_at = now
    return row, created


def refresh(db: Session, data) -> dict:
    require_owner()
    target = date.fromisoformat(data.target_date) if data.target_date else _local_today()
    now = _utc_naive()
    expired_rows = db.scalars(select(Recommendation).where(
        Recommendation.tenant_id == get_current_tenant_id(),
        Recommendation.owner_id == get_current_owner_id(),
        Recommendation.status.in_(tuple(UNRESOLVED_STATUSES)),
        Recommendation.expires_at.is_not(None), Recommendation.expires_at <= now,
    )).all()
    for expired in expired_rows:
        expired.status = "expired"
        expired.handled_at = now
        expired.data_version += 1
        expired.updated_at = now
    rules = _active_rules(db)
    created, unchanged, excluded = [], [], []
    for rule in rules:
        if rule.rule_type == "product_repurchase":
            candidates, rejected = _product_candidates(db, rule, target, now)
        elif rule.rule_type == "service_follow_up":
            candidates, rejected = _service_candidates(db, rule, target, now)
        else:
            candidates, rejected = _renewal_candidates(db, rule, target, now)
        excluded.extend({"rule_type": rule.rule_type, **item} for item in rejected)
        for candidate in candidates:
            row, was_created = _upsert_candidate(db, candidate, rule, target, now)
            (created if was_created else unchanged).append(row.id)
    db.commit()
    return {
        "status": "refreshed" if rules else "no_active_rules",
        "target_date": target.isoformat(), "created_ids": created,
        "unchanged_ids": unchanged, "excluded": excluded,
        "expired_ids": [row.id for row in expired_rows],
        "rules": [{"id": row.id, "type": row.rule_type, "version": row.version} for row in rules],
        "external_calls": {"chat_model": 0, "external_embedding": 0, "message_send": 0},
    }


def _recommendation(db: Session, recommendation_id: int) -> Recommendation:
    row = db.scalar(select(Recommendation).where(
        Recommendation.id == recommendation_id,
        Recommendation.tenant_id == get_current_tenant_id(),
        Recommendation.owner_id == get_current_owner_id(),
    ))
    if row is None:
        raise NotFoundError("今日事项不存在")
    return row


def _drafts(db: Session, recommendation_id: int) -> list[MessageDraft]:
    return list(db.scalars(select(MessageDraft).where(
        MessageDraft.tenant_id == get_current_tenant_id(),
        MessageDraft.recommendation_id == recommendation_id,
    ).order_by(MessageDraft.id)).all())


def _view(db: Session, row: Recommendation) -> dict:
    customer = db.scalar(select(Customer).where(
        Customer.id == row.customer_id, Customer.tenant_id == get_current_tenant_id(),
    ))
    subject_name = None
    if row.subject_type == "product":
        entity = db.scalar(select(Product).where(Product.id == row.subject_id, Product.tenant_id == get_current_tenant_id()))
        subject_name = entity.canonical_name if entity else None
    elif row.subject_type == "service":
        entity = db.scalar(select(Service).where(Service.id == row.subject_id, Service.tenant_id == get_current_tenant_id()))
        subject_name = entity.name if entity else None
    drafts = _drafts(db, row.id)
    result = {
        "id": row.id, "customer": {"id": row.customer_id, "display_name": customer.display_name if customer else "已删除客户"},
        "type": row.trigger_type, "subject": {"type": row.subject_type, "id": row.subject_id, "name": subject_name},
        "reason": row.reason, "suggested_action": row.suggested_action,
        "score": row.score, "score_breakdown": _load(row.score_breakdown_json, {}),
        "policy_version": row.policy_version, "rule_version": row.rule_version,
        "status": row.status, "unread": row.read_at is None, "read_at": row.read_at.isoformat() if row.read_at else None,
        "handled_at": row.handled_at.isoformat() if row.handled_at else None,
        "snoozed_until": row.snoozed_until.replace(tzinfo=timezone.utc).astimezone(SHANGHAI).isoformat() if row.snoozed_until else None,
        "data_version": row.data_version, "degraded": row.degraded,
        "degraded_reason": row.degraded_reason, "risk_flags": _load(row.risk_flags_json, []),
        "evidence": _load(row.evidence_snapshot, []),
        "knowledge_versions": _load(row.knowledge_versions, []),
        "message_drafts": [{
            "id": draft.id, "variant": draft.variant, "content": draft.content,
            "data_version": draft.data_version, "copy_only": True,
        } for draft in drafts],
        "external_send_available": False,
    }
    standard = next((draft for draft in drafts if draft.variant == "standard"), None)
    result["contract"] = _contract_view(row, standard.content if standard else "")
    return result


def _contract_view(row: Recommendation, owner_script: str) -> dict:
    evidence = []
    for index, item in enumerate(_load(row.evidence_snapshot, [])[:9]):
        if item.get("kind") == "transaction":
            source_type, source_id = "transaction", f"ledger-{item.get('entry_id')}"
            excerpt = f"{item.get('occurred_on')} 购买 {item.get('quantity')} 件"
        elif item.get("kind") == "package_balance":
            source_type = "transaction"
            source_id = f"package-{item.get('package_id') or item.get('ledger_entry_id')}"
            excerpt = f"权威余量 {item.get('remaining_count')} 次；证据日期 {item.get('last_consumed_at') or item.get('evidence_date')}"
        else:
            source_type, source_id = "catalog_knowledge", f"document-{item.get('document_id')}"
            excerpt = str(item.get("snippet") or f"当前已确认知识 v{item.get('knowledge_version')}")[:240]
        evidence.append({
            "evidence_id": f"r{row.id}-e{index + 1}", "source_type": source_type,
            "source_id": source_id, "excerpt": excerpt[:240],
        })
    evidence.append({
        "evidence_id": f"r{row.id}-rule", "source_type": "rule",
        "source_id": f"rule-{row.rule_id}-v{row.rule_version}",
        "excerpt": f"SQL权威规则 {row.trigger_type}；策略 {row.policy_version}"[:240],
    })
    if row.status in {"new", "viewed", "snoozed", "expired"}:
        contract_status = row.status
    elif row.status in {"contacted", "repurchased"}:
        contract_status = "adopted"
    else:
        contract_status = "dismissed"
    return {
        "recommendation_id": str(row.id), "customer_id": str(row.customer_id),
        "target_type": "product" if row.subject_type == "product" else "service",
        "target_id": str(row.subject_id) if row.subject_id is not None else None,
        "reason": (row.reason or "")[:300],
        "suggested_action": (row.suggested_action or "")[:200],
        "owner_script": owner_script[:500], "evidence": evidence,
        "risk_flags": _load(row.risk_flags_json, [])[:20],
        "score": round(min(max(float(row.score or 0) / 100, 0), 1), 4),
        "generated_at": (row.generated_at or row.created_at).replace(tzinfo=timezone.utc).isoformat(),
        "expires_at": (row.expires_at or row.created_at).replace(tzinfo=timezone.utc).isoformat(),
        "status": contract_status,
    }


def list_today(db: Session, *, scope: str = "top3", target_date: str | None = None) -> dict:
    require_owner()
    target = date.fromisoformat(target_date) if target_date else _local_today()
    now = _utc_naive()
    rows = db.scalars(select(Recommendation).where(
        Recommendation.tenant_id == get_current_tenant_id(),
        Recommendation.owner_id == get_current_owner_id(),
        Recommendation.status.in_(tuple(UNRESOLVED_STATUSES)),
        or_(
            Recommendation.generation_date == target.isoformat(),
            (Recommendation.status == "snoozed") & (Recommendation.snoozed_until <= now),
        ),
        or_(Recommendation.snoozed_until.is_(None), Recommendation.snoozed_until <= now),
    ).order_by(Recommendation.score.desc(), Recommendation.generated_at, Recommendation.id)).all()
    unique: list[Recommendation] = []
    seen_customers: set[int] = set()
    for row in rows:
        if row.customer_id in seen_customers:
            continue
        seen_customers.add(row.customer_id)
        unique.append(row)
    selected = unique if scope == "all" else unique[:3]
    items = [_view(db, row) for row in selected]
    return {
        "target_date": target.isoformat(), "scope": scope,
        "unresolved_count": len(selected),
        "unread_count": sum(1 for row in selected if row.read_at is None),
        "available_count": len(unique), "top_customer_limit": 3,
        "items": items,
        "ui_block": {
            "block_id": f"today-{get_current_tenant_id()}-{get_current_owner_id()}-{target.isoformat()}",
            "type": "today_tasks", "title": "今日事项", "subtitle": "逐条打开才会标记已读",
            "collapsible": False, "unread_count": sum(1 for row in selected if row.read_at is None),
            "tasks": [item["contract"] for item in items], "actions": [],
        },
    }


def get_detail(db: Session, recommendation_id: int) -> dict:
    require_owner()
    return _view(db, _recommendation(db, recommendation_id))


def _audit(db: Session, row: Recommendation, action: str, key: str, before: dict, after: dict) -> RecommendationActionAudit:
    existing = db.scalar(select(RecommendationActionAudit).where(
        RecommendationActionAudit.tenant_id == get_current_tenant_id(),
        RecommendationActionAudit.idempotency_key == key,
    ))
    if existing:
        return existing
    audit = RecommendationActionAudit(
        tenant_id=get_current_tenant_id(), owner_id=get_current_owner_id(),
        recommendation_id=row.id, action_type=action, idempotency_key=key,
        before_json=_json(before), after_json=_json(after), created_at=utcnow(),
    )
    db.add(audit)
    return audit


def mark_read(db: Session, recommendation_id: int, data) -> dict:
    require_owner()
    row = _recommendation(db, recommendation_id)
    existing = db.scalar(select(RecommendationActionAudit).where(
        RecommendationActionAudit.tenant_id == get_current_tenant_id(),
        RecommendationActionAudit.idempotency_key == data.idempotency_key,
    ))
    if existing:
        return {"status": row.status, "data_version": row.data_version, "idempotent_replay": True}
    if row.data_version != data.data_version:
        raise ConflictError("事项版本已变化，请刷新", {"status": "conflict", "data_version": row.data_version})
    before = {"status": row.status, "read_at": row.read_at.isoformat() if row.read_at else None}
    if row.read_at is None:
        row.read_at = utcnow()
        if row.status == "new":
            row.status = "viewed"
        row.data_version += 1
        row.updated_at = utcnow()
    _audit(db, row, "viewed", data.idempotency_key, before, {"status": row.status, "read_at": row.read_at.isoformat()})
    db.commit()
    return {"status": row.status, "data_version": row.data_version, "read_at": row.read_at.isoformat(), "idempotent_replay": False}


def _feedback_context(row: Recommendation) -> dict:
    return {
        "customer_ref": f"c-{row.customer_id}", "recommendation_ref": f"r-{row.id}",
        "trigger_type": row.trigger_type, "subject_type": row.subject_type,
        "subject_id": row.subject_id, "rule_version": row.rule_version,
        "evidence_checksum": _checksum(_load(row.evidence_snapshot, [])),
    }


def _validate_feedback_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        return None
    lowered = cleaned.lower()
    if SECRET_RE.search(cleaned) or any(term in lowered for term in INJECTION_TERMS):
        raise DomainError("反馈包含秘密或技术指令，已拒绝保存")
    return cleaned[:1000]


def _action_mutation(row: Recommendation, action: str, snoozed_until: datetime | None) -> None:
    now = utcnow()
    if action == "snoozed":
        target = _utc_naive(snoozed_until)
        if target <= now:
            raise DomainError("稍后时间必须晚于当前时间")
        row.status = "snoozed"
        row.snoozed_until = target
        row.handled_at = None
    elif action == "allow_recommendation":
        row.status = "cancelled"
        row.handled_at = now
    else:
        row.status = action
        row.handled_at = now
        row.snoozed_until = None
        if action == "contacted":
            row.contacted_at = now
    row.data_version += 1
    row.updated_at = now


def act(db: Session, recommendation_id: int, data) -> dict:
    require_owner()
    row = _recommendation(db, recommendation_id)
    existing = db.scalar(select(RecommendationActionAudit).where(
        RecommendationActionAudit.tenant_id == get_current_tenant_id(),
        RecommendationActionAudit.idempotency_key == data.idempotency_key,
    ))
    if existing:
        return {"status": row.status, "data_version": row.data_version, "idempotent_replay": True}
    if row.data_version != data.data_version:
        raise ConflictError("事项版本已变化，请刷新", {"status": "conflict", "data_version": row.data_version})
    before = {"status": row.status, "data_version": row.data_version, "snoozed_until": str(row.snoozed_until)}
    _action_mutation(row, data.action, data.snoozed_until)
    context = _feedback_context(row)
    db.add(FollowUpFeedback(
        tenant_id=get_current_tenant_id(), recommendation_id=row.id,
        owner_id=get_current_owner_id(), customer_id=row.customer_id,
        action_type=data.action, feedback_text=_validate_feedback_text(data.feedback_text),
        next_reminder_at=row.snoozed_until if data.action == "snoozed" else None,
        anonymous_context_json=_json(context), evidence_checksum=context["evidence_checksum"],
        rule_version=row.rule_version, idempotency_key=f"feedback-{data.idempotency_key}"[:128],
        status="recorded", data_version=1, created_at=utcnow(), updated_at=utcnow(),
    ))
    _audit(db, row, data.action, data.idempotency_key, before, {"status": row.status, "data_version": row.data_version})
    db.commit()
    return {"status": row.status, "data_version": row.data_version, "idempotent_replay": False}


def rewrite_message(db: Session, recommendation_id: int, data) -> dict:
    require_owner()
    row = _recommendation(db, recommendation_id)
    customer = db.scalar(select(Customer).where(Customer.id == row.customer_id, Customer.tenant_id == get_current_tenant_id()))
    if customer is None:
        raise NotFoundError("客户不存在或已删除")
    if row.subject_type == "product":
        entity = db.scalar(select(Product).where(Product.id == row.subject_id, Product.tenant_id == get_current_tenant_id()))
        subject = entity.canonical_name if entity else "相关产品"
    else:
        entity = db.scalar(select(Service).where(Service.id == row.subject_id, Service.tenant_id == get_current_tenant_id()))
        subject = entity.name if entity else "相关服务"
    remaining = None
    for item in _load(row.evidence_snapshot, []):
        if item.get("kind") == "package_balance":
            remaining = item.get("remaining_count")
            break
    content = _safe_message(row.trigger_type, customer=customer.display_name, subject=subject, remaining=remaining, variant=data.variant)
    draft = db.scalar(select(MessageDraft).where(
        MessageDraft.tenant_id == get_current_tenant_id(),
        MessageDraft.recommendation_id == row.id, MessageDraft.variant == data.variant,
    ))
    replay = draft is not None
    if draft is None:
        draft = MessageDraft(
            tenant_id=get_current_tenant_id(), recommendation_id=row.id, variant=data.variant,
            content=content, checksum=_checksum({"content": content}), data_version=1,
            created_at=utcnow(), updated_at=utcnow(),
        )
        db.add(draft)
        db.commit()
    return {"draft": {"id": draft.id, "variant": draft.variant, "content": draft.content, "data_version": draft.data_version}, "idempotent_replay": replay, "external_calls": 0}


def copy_message(db: Session, recommendation_id: int, draft_id: int, data) -> dict:
    require_owner()
    row = _recommendation(db, recommendation_id)
    draft = db.scalar(select(MessageDraft).where(
        MessageDraft.id == draft_id, MessageDraft.tenant_id == get_current_tenant_id(),
        MessageDraft.recommendation_id == row.id,
    ))
    if draft is None:
        raise NotFoundError("话术草稿不存在")
    if draft.data_version != data.data_version:
        raise ConflictError("话术版本已变化，请刷新", {"status": "conflict", "data_version": draft.data_version})
    existing = db.scalar(select(RecommendationActionAudit).where(
        RecommendationActionAudit.tenant_id == get_current_tenant_id(),
        RecommendationActionAudit.idempotency_key == data.idempotency_key,
    ))
    if not existing:
        draft.copied_at = utcnow()
        _audit(db, row, "copied", data.idempotency_key, {"copied_at": None}, {"copied_at": draft.copied_at.isoformat()})
        db.commit()
    return {"content": draft.content, "copy_only": True, "external_send": False, "status": row.status, "idempotent_replay": existing is not None}


def _extract_followup(text: str | None) -> tuple[datetime | None, dict | None]:
    if not text:
        return None, None
    now_local = datetime.now(SHANGHAI)
    reminder = None
    match = DATE_RE.search(text)
    if match:
        try:
            reminder = datetime.combine(date(int(match[1]), int(match[2]), int(match[3])), time(9, 0), tzinfo=SHANGHAI)
        except ValueError:
            reminder = None
    else:
        later = DAY_LATER_RE.search(text)
        if later and 1 <= int(later[1]) <= 365:
            reminder = now_local + timedelta(days=int(later[1]))
    preference = PREFERENCE_RE.search(text)
    fact = None
    if preference:
        value = preference.group(1).strip()
        if value and not any(term in value.lower() for term in INJECTION_TERMS) and not SECRET_RE.search(value):
            fact = {
                "type": "upsert_customer_fact", "fact_type": "preference",
                "display_value": value, "normalized_value": value.lower(),
                "evidence_text": preference.group(0).strip(), "confidence": 1.0,
                "sensitivity_level": "normal", "supersedes_id": None,
            }
    return reminder, fact


def feedback(db: Session, recommendation_id: int, data) -> dict:
    require_owner()
    row = _recommendation(db, recommendation_id)
    existing = db.scalar(select(FollowUpFeedback).where(
        FollowUpFeedback.tenant_id == get_current_tenant_id(),
        FollowUpFeedback.idempotency_key == data.idempotency_key,
    ))
    if existing:
        return {"feedback_id": existing.id, "proposal": None, "idempotent_replay": True}
    if row.data_version != data.data_version:
        raise ConflictError("事项版本已变化，请刷新", {"status": "conflict", "data_version": row.data_version})
    cleaned = _validate_feedback_text(data.feedback_text)
    reminder, fact = _extract_followup(cleaned)
    if data.snoozed_until:
        reminder = data.snoozed_until
    # 反馈状态本身是权威操作；从原文提取的事实/下次时间仍只进入 Proposal。
    mapped_action = data.action if data.action != "ai_inaccurate" else "viewed"
    if data.action == "snoozed" and data.snoozed_until is None:
        # 从自由文本提取的下次时间只能进入 Proposal，确认前不改变提醒状态。
        mapped_action = "viewed"
    if mapped_action != "viewed":
        before = {"status": row.status, "data_version": row.data_version}
        _action_mutation(row, mapped_action, None if reminder and data.snoozed_until is None else data.snoozed_until)
        _audit(db, row, mapped_action, f"action-{data.idempotency_key}"[:128], before, {"status": row.status, "data_version": row.data_version})
    context = _feedback_context(row)
    feedback_row = FollowUpFeedback(
        tenant_id=get_current_tenant_id(), recommendation_id=row.id,
        owner_id=get_current_owner_id(), customer_id=row.customer_id,
        action_type=data.action, feedback_text=cleaned,
        extracted_facts_json=None, next_reminder_at=None, proposal_id=None,
        anonymous_context_json=_json(context), evidence_checksum=context["evidence_checksum"],
        rule_version=row.rule_version, idempotency_key=data.idempotency_key,
        status="recorded", data_version=1, created_at=utcnow(), updated_at=utcnow(),
    )
    db.add(feedback_row)
    db.flush()
    actions = []
    if fact:
        current_fact = db.scalar(select(CustomerFact).where(
            CustomerFact.tenant_id == get_current_tenant_id(),
            CustomerFact.customer_id == row.customer_id,
            CustomerFact.fact_type == fact["fact_type"],
            CustomerFact.confirmation_status == "confirmed",
            CustomerFact.valid_to.is_(None), CustomerFact.deleted_at.is_(None),
        ).order_by(CustomerFact.id.desc()).limit(1))
        fact["normalized_value"] = normalize_fact_value(fact["display_value"])
        fact["supersedes_id"] = current_fact.id if current_fact else None
        actions.append(fact)
    if reminder:
        target = _utc_naive(reminder)
        if target > utcnow():
            actions.append({
                "type": "snooze_recommendation", "recommendation_id": row.id,
                "feedback_id": feedback_row.id, "snoozed_until": target.isoformat(),
            })
    proposal = None
    if actions:
        feedback_row.status = "proposal_pending"
        db.flush()
        parsed = {
            "title": "确认从反馈提取的客户事实或下次时间",
            "customer": {"customer_id": row.customer_id, "new_customer": None},
            "actions": actions,
            "precheck": "确认时重新检查客户、推荐事项版本与事实版本；确认前不写客户事实或提醒",
        }
        result = _create_proposal(
            db, parsed=parsed, original_input=cleaned or "店主反馈",
            request_id=data.request_id, idempotency_key=f"proposal-{data.idempotency_key}"[:128],
            block_type="feedback_confirm_card",
        )
        proposal = result["proposal"]
        feedback_row.proposal_id = proposal["id"]
        db.commit()
    else:
        db.commit()
    return {"feedback_id": feedback_row.id, "status": row.status, "proposal": proposal, "idempotent_replay": False, "external_calls": 0}


def stage_status(db: Session) -> dict:
    require_owner()
    tenant_id = get_current_tenant_id()
    owner_id = get_current_owner_id()
    return {
        "stage": 6,
        "counts": {
            "active_rules": db.scalar(select(func.count(RecommendationRule.id)).where(
                RecommendationRule.tenant_id == tenant_id, RecommendationRule.status == "active",
            )) or 0,
            "recommendations": db.scalar(select(func.count(Recommendation.id)).where(
                Recommendation.tenant_id == tenant_id, Recommendation.owner_id == owner_id,
            )) or 0,
            "message_drafts": db.scalar(select(func.count(MessageDraft.id)).join(
                Recommendation, Recommendation.id == MessageDraft.recommendation_id,
            ).where(MessageDraft.tenant_id == tenant_id, Recommendation.tenant_id == tenant_id, Recommendation.owner_id == owner_id)) or 0,
            "feedback": db.scalar(select(func.count(FollowUpFeedback.id)).where(
                FollowUpFeedback.tenant_id == tenant_id, FollowUpFeedback.owner_id == owner_id,
            )) or 0,
        },
        "capabilities": {
            "sql_authoritative_rules": True, "hard_exclusions_before_score": True,
            "top3_unique_customers": True, "stable_rag_snapshot": True,
            "deterministic_safe_templates": True, "copy_only_no_send": True,
            "read_and_handled_separate": True, "feedback_proposal_confirmation": True,
            "owner_rule_editing": False, "stage7_runner": False,
        },
        "runtime": {
            "chat_model_calls": 0, "external_embedding_calls": 0,
            "external_message_sends": 0, "real_model_enabled": False,
            "timezone": "Asia/Shanghai",
        },
    }
