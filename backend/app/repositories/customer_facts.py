"""阶段4客户事实仓储：只返回已确认当前版本，不静默覆盖冲突。"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tenant import get_current_tenant_id
from app.infrastructure.models import CustomerFact


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def list_current(db: Session, customer_id: int) -> list[CustomerFact]:
    return list(
        db.scalars(
            select(CustomerFact).where(
                CustomerFact.tenant_id == get_current_tenant_id(),
                CustomerFact.customer_id == customer_id,
                CustomerFact.confirmation_status == "confirmed",
                CustomerFact.valid_to.is_(None),
                CustomerFact.deleted_at.is_(None),
            ).order_by(CustomerFact.fact_type, CustomerFact.id)
        ).all()
    )


def get_current_by_type(db: Session, customer_id: int, fact_type: str) -> CustomerFact | None:
    return db.scalar(
        select(CustomerFact).where(
            CustomerFact.tenant_id == get_current_tenant_id(),
            CustomerFact.customer_id == customer_id,
            CustomerFact.fact_type == fact_type,
            CustomerFact.confirmation_status == "confirmed",
            CustomerFact.valid_to.is_(None),
            CustomerFact.deleted_at.is_(None),
        ).order_by(CustomerFact.id.desc()).limit(1)
    )


def create_confirmed(
    db: Session,
    *,
    customer_id: int,
    fact_type: str,
    display_value: str,
    normalized_value: str,
    evidence_text: str,
    source_type: str,
    source_id: str | None,
    confidence: float | None,
    sensitivity_level: str,
    supersedes_id: int | None,
) -> CustomerFact:
    now = _utcnow()
    previous = get_current_by_type(db, customer_id, fact_type)
    if previous and previous.id != supersedes_id:
        # 确认时权威版本应已由快照校验；这里仍拒绝意外覆盖。
        if previous.normalized_value != normalized_value:
            from app.domain.errors import ConflictError

            raise ConflictError("客户事实已变化，请重新确认", {"status": "stale"})
    if previous and previous.normalized_value == normalized_value:
        return previous
    if previous:
        previous.valid_to = now
        previous.updated_at = now

    row = CustomerFact(
        tenant_id=get_current_tenant_id(), customer_id=customer_id, fact_type=fact_type,
        display_value=display_value, normalized_value=normalized_value,
        evidence_text=evidence_text, source_type=source_type, source_id=source_id,
        confidence=confidence, confirmation_status="confirmed",
        sensitivity_level=sensitivity_level, valid_from=now,
        supersedes_id=previous.id if previous else None,
    )
    db.add(row)
    db.flush()
    return row


def retract_current(
    db: Session, *, customer_id: int, fact_id: int, evidence_text: str, source_id: str | None
) -> tuple[CustomerFact, CustomerFact]:
    current = db.scalar(
        select(CustomerFact).where(
            CustomerFact.id == fact_id,
            CustomerFact.tenant_id == get_current_tenant_id(),
            CustomerFact.customer_id == customer_id,
            CustomerFact.confirmation_status == "confirmed",
            CustomerFact.valid_to.is_(None),
            CustomerFact.deleted_at.is_(None),
        )
    )
    if current is None:
        from app.domain.errors import ConflictError

        raise ConflictError("要撤销的客户事实已变化，请重新确认", {"status": "stale"})
    now = _utcnow()
    current.valid_to = now
    current.updated_at = now
    retraction = CustomerFact(
        tenant_id=get_current_tenant_id(), customer_id=customer_id,
        fact_type=current.fact_type, display_value=current.display_value,
        normalized_value=current.normalized_value, evidence_text=evidence_text,
        source_type="conversation_retraction", source_id=source_id,
        confidence=None, confirmation_status="retracted",
        sensitivity_level=current.sensitivity_level, valid_from=now, valid_to=now,
        supersedes_id=current.id,
    )
    db.add(retraction)
    db.flush()
    return current, retraction
