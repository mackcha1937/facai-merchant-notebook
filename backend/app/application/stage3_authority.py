"""Proposal 创建/确认时使用的权威对象快照。"""
import json

from sqlalchemy.orm import Session

from app.domain.errors import DomainError
from app.repositories import customers as customer_repo
from app.repositories import packages as package_repo
from app.repositories import services as service_repo


def build_authority_snapshot(db: Session, parsed: dict) -> dict:
    customer_id = (parsed.get("customer") or {}).get("customer_id")
    customer = customer_repo.get_customer(db, customer_id) if customer_id else None
    if customer is None:
        raise DomainError("客户不存在或已删除")

    snapshot = {
        "customer": {
            "id": customer.id,
            "updated_at": customer.updated_at.isoformat() if customer.updated_at else None,
            "deleted": customer.deleted_at is not None,
        },
        "actions": [],
    }
    for action in parsed.get("actions") or []:
        item = {"type": action.get("type")}
        service_id = action.get("service_id")
        if service_id:
            service = service_repo.get_service(db, service_id)
            item["service"] = {
                "id": service_id,
                "status": service.status if service else "missing",
            }
        if action.get("type") == "consume_service" and service_id:
            packages = package_repo.list_packages_for_customer_service(db, customer.id, service_id)
            if action.get("package_id"):
                packages = [p for p in packages if p.id == action["package_id"]]
            used = package_repo.compute_used_counts(db, packages)
            item["packages"] = [
                {
                    "id": p.id,
                    "total_count": p.total_count,
                    "opening_used_count": p.opening_used_count,
                    "used_count": used[p.id],
                    "remaining_count": p.total_count - used[p.id],
                    "status": p.status,
                    "deleted": p.deleted_at is not None,
                }
                for p in packages
            ]
        snapshot["actions"].append(item)
    return snapshot


def snapshot_diff(before: dict, current: dict) -> list[dict]:
    if before == current:
        return []
    differences: list[dict] = []
    if before.get("customer") != current.get("customer"):
        differences.append(
            {"object": "customer", "before": before.get("customer"), "current": current.get("customer")}
        )
    before_actions = before.get("actions") or []
    current_actions = current.get("actions") or []
    for index in range(max(len(before_actions), len(current_actions))):
        old = before_actions[index] if index < len(before_actions) else None
        new = current_actions[index] if index < len(current_actions) else None
        if old != new:
            differences.append({"object": f"action[{index}]", "before": old, "current": new})
    return differences


def canonical_json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
