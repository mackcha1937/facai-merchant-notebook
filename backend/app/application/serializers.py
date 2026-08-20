"""ORM 对象转字典（输出给 API）。"""
from app.domain.rules import remaining_count
from app.infrastructure.models import Customer, LedgerEntry, Package, Service


def alias_to_dict(alias) -> dict:
    return {"id": alias.id, "alias": alias.alias}


def customer_to_dict(customer: Customer) -> dict:
    aliases = [a for a in customer.aliases if a.deleted_at is None]
    return {
        "id": customer.id,
        "display_name": customer.display_name,
        "aliases": [alias_to_dict(a) for a in aliases],
    }


def service_to_dict(service: Service) -> dict:
    return {"id": service.id, "name": service.name, "status": service.status}


def derive_package_status(package: Package, remaining: int) -> str:
    """套餐状态由权威余额派生：手动停用为 inactive，剩余0为 exhausted，否则 active。"""
    if package.status == "inactive":
        return "inactive"
    return "exhausted" if remaining <= 0 else "active"


def package_to_dict(package: Package, used_count: int | None = None) -> dict:
    if used_count is None:
        used_count = package.opening_used_count
    remaining = remaining_count(package.total_count, used_count)
    return {
        "id": package.id,
        "customer_id": package.customer_id,
        "service_id": package.service_id,
        "service_name": package.service.name if package.service else None,
        "total_count": package.total_count,
        "opening_used_count": package.opening_used_count,
        "used_count": used_count,
        "remaining_count": remaining,
        "price_cents": package.price_cents,
        "purchased_on": package.purchased_on,
        "status": derive_package_status(package, remaining),
    }


def packages_to_dicts(db, packages: list[Package]) -> list[dict]:
    """批量序列化套餐，并带权威累计已用（避免 N+1）。"""
    from app.repositories.packages import compute_used_counts

    used_counts = compute_used_counts(db, packages)
    return [package_to_dict(p, used_counts.get(p.id, p.opening_used_count)) for p in packages]


def ledger_to_dict(entry: LedgerEntry) -> dict:
    return {
        "id": entry.id,
        "customer_id": entry.customer_id,
        "entry_type": entry.entry_type,
        "package_id": entry.package_id,
        "service_id": entry.service_id,
        "service_name": entry.service.name if entry.service else None,
        "product_name": entry.product_name,
        "quantity": entry.quantity,
        "price_cents": entry.price_cents,
        "occurred_on": entry.occurred_on,
    }


def save(db) -> None:
    """提交事务；失败则回滚并继续抛出异常。"""
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
