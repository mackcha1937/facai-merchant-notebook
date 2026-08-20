"""客户查询读模型：最后消费聚合、客户概览、服务类型摘要、服务详情。

“最后消费”只统计未删除的 package_consumption 与 one_time_service，
package_purchase 与 product_purchase 不参与。
"""
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.application import serializers
from app.domain.errors import NotFoundError
from app.infrastructure.models import LedgerEntry, Package
from app.repositories import customers as customer_repo
from app.repositories import ledger as ledger_repo
from app.repositories import packages as package_repo
from app.repositories import services as service_repo

_CONSUME_TYPES = ("package_consumption", "one_time_service")


def _date_to_int(value) -> int:
    try:
        y, m, d = str(value).split("-")
        return int(y) * 10000 + int(m) * 100 + int(d)
    except Exception:  # noqa: BLE001
        return 0


def _sort_key(summary: dict):
    at = summary.get("last_consumed_at")
    if not at:
        return (1, 0)
    return (0, -_date_to_int(at))


def _last_consumption(db: Session, customer_id: int, service_id: int | None = None) -> LedgerEntry | None:
    stmt = (
        select(LedgerEntry)
        .where(
            LedgerEntry.customer_id == customer_id,
            LedgerEntry.entry_type.in_(_CONSUME_TYPES),
            LedgerEntry.deleted_at.is_(None),
        )
        .options(selectinload(LedgerEntry.service))
    )
    if service_id is not None:
        stmt = stmt.where(LedgerEntry.service_id == service_id)
    stmt = stmt.order_by(LedgerEntry.occurred_on.desc(), LedgerEntry.id.desc()).limit(1)
    return db.scalar(stmt)


def _service_ids_for_customer(db: Session, customer_id: int) -> set[int]:
    pkg_ids = set(
        db.scalars(
            select(Package.service_id).where(
                Package.customer_id == customer_id, Package.deleted_at.is_(None)
            )
        ).all()
    )
    ledger_ids = set(
        db.scalars(
            select(LedgerEntry.service_id).where(
                LedgerEntry.customer_id == customer_id,
                LedgerEntry.service_id.is_not(None),
                LedgerEntry.deleted_at.is_(None),
            )
        ).all()
    )
    return pkg_ids | ledger_ids


def list_customer_summaries(db: Session, search: str | None = None, sort: str = "last_consumed_desc") -> list[dict]:
    customers = customer_repo.list_customers(db, search)
    summaries = []
    for c in customers:
        last = _last_consumption(db, c.id)
        summaries.append(
            {
                "id": c.id,
                "display_name": c.display_name,
                "aliases": [a.alias for a in c.aliases if a.deleted_at is None],
                "last_consumed_service_name": last.service.name if last and last.service else None,
                "last_consumed_at": last.occurred_on if last else None,
                "service_type_count": len(_service_ids_for_customer(db, c.id)),
            }
        )
    if sort == "last_consumed_desc":
        summaries.sort(key=_sort_key)
    return summaries


def list_customer_services(db: Session, customer_id: int) -> list[dict]:
    if customer_repo.get_customer(db, customer_id) is None:
        raise NotFoundError("客户不存在或已删除")

    result = []
    for sid in sorted(_service_ids_for_customer(db, customer_id)):
        service = service_repo.get_service_any(db, sid)
        if service is None:
            continue
        packages = package_repo.list_packages_for_customer_service(db, customer_id, sid)
        used_counts = package_repo.compute_used_counts(db, packages)
        active_count = sum(1 for p in packages if serializers.derive_package_status(p, p.total_count - used_counts[p.id]) == "active")
        last = _last_consumption(db, customer_id, service_id=sid)
        result.append(
            {
                "service_id": sid,
                "service_name": service.name,
                "service_status": service.status,
                "last_consumed_at": last.occurred_on if last else None,
                "active_package_count": active_count,
                "total_remaining_count": (
                    sum(p.total_count - used_counts[p.id] for p in packages) if packages else None
                ),
                "is_one_time_only": len(packages) == 0,
            }
        )

    # 有有效套餐的服务优先，其余按最后消费倒序；停用服务靠后
    def key(s):
        rank = 0 if s["active_package_count"] > 0 else (2 if s["service_status"] != "active" else 1)
        return (rank, -_date_to_int(s["last_consumed_at"] or ""))

    result.sort(key=key)
    return result


def get_customer_overview(db: Session, customer_id: int) -> dict:
    customer = customer_repo.get_customer(db, customer_id)
    if customer is None:
        raise NotFoundError("客户不存在或已删除")

    services = list_customer_services(db, customer_id)
    packages = package_repo.list_packages_for_customer(db, customer_id)
    used_counts = package_repo.compute_used_counts(db, packages)
    active_package_count = sum(
        1 for p in packages if serializers.derive_package_status(p, p.total_count - used_counts[p.id]) == "active"
    )

    recent = list(
        db.scalars(
            select(LedgerEntry)
            .where(LedgerEntry.customer_id == customer_id, LedgerEntry.deleted_at.is_(None))
            .options(selectinload(LedgerEntry.service))
            .order_by(LedgerEntry.occurred_on.desc(), LedgerEntry.id.desc())
            .limit(5)
        ).all()
    )

    last = _last_consumption(db, customer_id)
    return {
        "id": customer.id,
        "display_name": customer.display_name,
        "aliases": [a.alias for a in customer.aliases if a.deleted_at is None],
        "last_consumed_at": last.occurred_on if last else None,
        "service_type_count": len(services),
        "active_package_count": active_package_count,
        "services": services,
        "recent_entries": [serializers.ledger_to_dict(e) for e in recent],
    }


def get_customer_service_detail(db: Session, customer_id: int, service_id: int) -> dict:
    customer = customer_repo.get_customer(db, customer_id)
    if customer is None:
        raise NotFoundError("客户不存在或已删除")
    service = service_repo.get_service_any(db, service_id)
    if service is None:
        raise NotFoundError("服务项目不存在")

    packages = package_repo.list_packages_for_customer_service(db, customer_id, service_id)
    used_counts = package_repo.compute_used_counts(db, packages)
    package_dicts = [serializers.package_to_dict(p, used_counts[p.id]) for p in packages]

    history = ledger_repo.list_ledger_for_customer_service(db, customer_id, service_id)
    last = _last_consumption(db, customer_id, service_id=service_id)

    return {
        "customer_id": customer.id,
        "customer_display_name": customer.display_name,
        "service_id": service.id,
        "service_name": service.name,
        "service_status": service.status,
        "last_consumed_at": last.occurred_on if last else None,
        "is_one_time_only": len(packages) == 0,
        "packages": package_dicts,
        "history": [serializers.ledger_to_dict(e) for e in history],
    }
