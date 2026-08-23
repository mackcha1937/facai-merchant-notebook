"""Proposal 创建/确认时使用的权威对象快照。"""
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import DomainError
from app.repositories import customers as customer_repo
from app.repositories import packages as package_repo
from app.repositories import services as service_repo
from app.repositories import customer_facts as fact_repo
from app.repositories import products as product_repo
from app.infrastructure.models import FollowUpFeedback, Recommendation
from app.core.tenant import get_current_owner_id, get_current_tenant_id


def build_authority_snapshot(db: Session, parsed: dict) -> dict:
    customer_id = (parsed.get("customer") or {}).get("customer_id")
    customer = customer_repo.get_customer(db, customer_id) if customer_id else None
    customer_required = any(
        action.get("type") in {
            "create_package", "consume_service", "record_one_time_service",
            "record_product_purchase", "query_customer", "upsert_customer_fact",
            "delete_customer_fact",
        }
        for action in parsed.get("actions") or []
    )
    if customer_required and customer is None:
        raise DomainError("客户不存在或已删除")

    snapshot = {
        "customer": ({
            "id": customer.id,
            "updated_at": customer.updated_at.isoformat() if customer.updated_at else None,
            "deleted": customer.deleted_at is not None,
        } if customer else None),
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
        if action.get("type") == "record_product_purchase" and action.get("product_id"):
            product = product_repo.get_product(db, action["product_id"], include_replaced=True)
            item["product"] = _product_snapshot(product, action["product_id"])
        if action.get("type") == "upsert_customer_fact" and customer:
            current = fact_repo.get_current_by_type(db, customer.id, action.get("fact_type"))
            item["current_fact"] = {
                "id": current.id,
                "normalized_value": current.normalized_value,
                "valid_to": current.valid_to.isoformat() if current.valid_to else None,
                "updated_at": current.updated_at.isoformat() if current.updated_at else None,
            } if current else None
        if action.get("type") == "delete_customer_fact" and customer:
            current = fact_repo.get_current_by_type(db, customer.id, action.get("fact_type"))
            item["current_fact"] = {
                "id": current.id,
                "normalized_value": current.normalized_value,
                "valid_to": current.valid_to.isoformat() if current.valid_to else None,
                "updated_at": current.updated_at.isoformat() if current.updated_at else None,
            } if current else None
        if action.get("type") == "create_product":
            item["identity"] = {
                "canonical_name": action.get("canonical_name"),
                "brand": action.get("brand"),
                "specification": action.get("specification"),
            }
        if action.get("type") == "merge_product":
            source = product_repo.get_product(db, action.get("source_product_id"), include_replaced=True)
            target = product_repo.get_product(db, action.get("target_product_id"), include_replaced=True)
            item["source"] = _product_snapshot(source, action.get("source_product_id"))
            item["target"] = _product_snapshot(target, action.get("target_product_id"))
        if action.get("type") in {"publish_knowledge", "withdraw_knowledge"}:
            from app.application.knowledge_service import authority_state

            item["knowledge_authority"] = authority_state(
                db, action.get("entity_type"), action.get("entity_id")
            )
        if action.get("type") == "snooze_recommendation":
            recommendation = db.scalar(select(Recommendation).where(
                Recommendation.id == action.get("recommendation_id"),
                Recommendation.tenant_id == get_current_tenant_id(),
                Recommendation.owner_id == get_current_owner_id(),
            ))
            feedback = db.scalar(select(FollowUpFeedback).where(
                FollowUpFeedback.id == action.get("feedback_id"),
                FollowUpFeedback.tenant_id == get_current_tenant_id(),
                FollowUpFeedback.owner_id == get_current_owner_id(),
            ))
            item["recommendation"] = ({
                "id": recommendation.id, "status": recommendation.status,
                "data_version": recommendation.data_version,
                "snoozed_until": recommendation.snoozed_until.isoformat() if recommendation.snoozed_until else None,
            } if recommendation else None)
            item["feedback"] = ({
                "id": feedback.id, "status": feedback.status,
                "data_version": feedback.data_version,
            } if feedback else None)
        snapshot["actions"].append(item)
    return snapshot


def _product_snapshot(product, requested_id: int | None) -> dict:
    if product is None:
        return {"id": requested_id, "status": "missing"}
    return {
        "id": product.id,
        "version": product.version,
        "lifecycle_status": product.lifecycle_status,
        "knowledge_status": product.knowledge_status,
        "merged_into_id": product.merged_into_id,
        "deleted": product.deleted_at is not None,
    }


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
