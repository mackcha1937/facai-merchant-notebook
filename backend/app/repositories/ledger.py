"""账本记录数据访问。"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.infrastructure.models import LedgerEntry


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def list_ledger_for_customer(db: Session, customer_id: int) -> list[LedgerEntry]:
    return list(
        db.scalars(
            select(LedgerEntry)
            .where(LedgerEntry.customer_id == customer_id, LedgerEntry.deleted_at.is_(None))
            .options(selectinload(LedgerEntry.service))
            .order_by(LedgerEntry.id.desc())
        ).all()
    )


def get_ledger_entry(db: Session, entry_id: int) -> LedgerEntry | None:
    return db.scalar(
        select(LedgerEntry).where(
            LedgerEntry.id == entry_id, LedgerEntry.deleted_at.is_(None)
        )
    )


def get_ledger_entry_any(db: Session, entry_id: int) -> LedgerEntry | None:
    """含已删除，用于恢复。"""
    return db.scalar(select(LedgerEntry).where(LedgerEntry.id == entry_id))


def create_ledger_entry(
    db: Session,
    customer_id: int,
    entry_type: str,
    service_id: int | None,
    product_name: str | None,
    quantity: int,
    price_cents: int | None,
    occurred_on: str | None,
) -> LedgerEntry:
    entry = LedgerEntry(
        customer_id=customer_id,
        entry_type=entry_type,
        service_id=service_id,
        product_name=product_name,
        quantity=quantity,
        price_cents=price_cents,
        occurred_on=occurred_on,
    )
    db.add(entry)
    db.flush()
    return entry


def soft_delete_ledger_entry(db: Session, entry: LedgerEntry) -> None:
    entry.deleted_at = _utcnow()
    db.flush()


def restore_ledger_entry(db: Session, entry: LedgerEntry) -> None:
    entry.deleted_at = None
    db.flush()
