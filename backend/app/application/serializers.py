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


def package_to_dict(package: Package) -> dict:
    return {
        "id": package.id,
        "customer_id": package.customer_id,
        "service_id": package.service_id,
        "service_name": package.service.name if package.service else None,
        "total_count": package.total_count,
        "used_count": package.used_count,
        "remaining_count": remaining_count(package.total_count, package.used_count),
        "price_cents": package.price_cents,
        "purchased_on": package.purchased_on,
        "status": package.status,
    }


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
