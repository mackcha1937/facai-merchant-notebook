"""只为阶段6本地浏览器验收装载开发包虚构数据。

必须使用 /private/tmp/facai-stage6-browser-* 下的隔离 SQLite；拒绝正式库。
不调用模型、外部 Embedding 或消息发送。
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import func, select

from app.application import recommendation_service
from app.core.config import get_settings
from app.core.database import get_session_factory
from app.core.tenant import set_current_owner_id, set_current_role, set_current_tenant_id
from app.infrastructure.models import (
    Customer, CustomerAlias, KnowledgeDocument, LedgerEntry, Package, Product,
    Recommendation, RecommendationRule, Service,
)
from app.schemas.recommendation import RecommendationRefreshRequest


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "v2.0" / "facai-v2-development-package" / "data"


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def main() -> None:
    settings = get_settings()
    url = settings.effective_database_url
    if "sqlite:////private/tmp/facai-stage6-browser-" not in url:
        raise RuntimeError("阶段6浏览器fixture只允许写入/private/tmp隔离库")
    if settings.enable_v2_real_model:
        raise RuntimeError("阶段6浏览器验收必须关闭真实模型")
    db = get_session_factory()()
    set_current_tenant_id(1); set_current_owner_id(1); set_current_role("owner")
    try:
        products = load("products.json")
        services = load("services.json")
        customers = load("customers.json")
        knowledge = [json.loads(line) for line in (DATA / "knowledge-documents.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]

        product_map = {}
        for item in products:
            row = Product(
                tenant_id=1, owner_id=1, canonical_name=item["name"], category=item["category"],
                lifecycle_status="active", knowledge_status="complete", version=1,
            )
            db.add(row); db.flush(); product_map[item["product_id"]] = row
        service_map = {}
        for item in services:
            row = Service(tenant_id=1, name=item["name"], status="active")
            db.add(row); db.flush(); service_map[item["service_id"]] = row
        customer_map = {}
        for item in customers:
            row = Customer(tenant_id=1, display_name=item["wechat_remark"])
            db.add(row); db.flush(); customer_map[item["customer_id"]] = row
            for alias in item["aliases"]:
                db.add(CustomerAlias(tenant_id=1, customer_id=row.id, alias=alias))

        # REC-001等价：开发包小红购买面膜，隔离验收日期距购买超过60天。
        red = customer_map["cus_red_001"]
        mask = product_map["prod_mask_soothing_001"]
        db.add(LedgerEntry(
            tenant_id=1, customer_id=red.id, entry_type="product_purchase", product_id=mask.id,
            product_name=mask.canonical_name, quantity=1, occurred_on="2026-06-01",
            original_input="阶段6浏览器隔离虚构数据",
        ))
        # REC-004：小蓝肩颈卡权威余量2，上次核销超过14天。
        blue = customer_map["cus_blue_001"]
        neck = service_map["svc_neck_001"]
        neck_package = Package(
            tenant_id=1, customer_id=blue.id, service_id=neck.id, total_count=3,
            opening_used_count=0, purchased_on="2026-05-01", status="active",
        )
        db.add(neck_package); db.flush()
        db.add(LedgerEntry(
            tenant_id=1, customer_id=blue.id, entry_type="package_consumption",
            package_id=neck_package.id, service_id=neck.id, quantity=1,
            occurred_on="2026-07-20", original_input="阶段6浏览器隔离虚构数据",
        ))
        # 第三位Top3客户仍使用开发包虚构实体；同时保留小黄清洁剩3次不触发续费。
        yellow = customer_map["cus_yellow_001"]
        serum = product_map["prod_serum_hydrate_001"]
        db.add(LedgerEntry(
            tenant_id=1, customer_id=yellow.id, entry_type="product_purchase", product_id=serum.id,
            product_name=serum.canonical_name, quantity=1, occurred_on="2026-05-01",
            original_input="阶段6浏览器隔离虚构数据",
        ))
        clean = service_map["svc_facial_clean_001"]
        db.add(Package(
            tenant_id=1, customer_id=yellow.id, service_id=clean.id, total_count=10,
            opening_used_count=7, purchased_on="2026-03-01", status="active",
        ))

        for item in knowledge:
            entity = product_map.get(item["catalog_id"]) or service_map.get(item["catalog_id"])
            if entity is None:
                continue
            entity_type = "product" if isinstance(entity, Product) else "service"
            db.add(KnowledgeDocument(
                tenant_id=1, entity_type=entity_type, entity_id=entity.id, knowledge_version=1,
                text=item["content"], metadata_json=json.dumps({"title": item["title"]}, ensure_ascii=False),
                status="published", checksum=f"browser-{item['document_id']}",
                source_type=item["source_type"], source_name=item["source_name"],
                confirmed=True, active=True,
            ))
        for rule_type, conditions, priority in (
            ("product_repurchase", {"days_since_purchase": 60}, 30),
            ("service_follow_up", {"days_since_service": 14}, 20),
            ("package_renewal", {"remaining_at_most": 2}, 10),
        ):
            db.add(RecommendationRule(
                tenant_id=1, rule_type=rule_type, version=1,
                conditions_json=json.dumps(conditions), hard_exclusions_json=json.dumps(["refusal", "adverse", "inactive", "knowledge", "cooldown"]),
                score_config_json=json.dumps({"base": 50, "overdue_per_day": 0.5, "evidence": 8, "low_balance": 12}),
                policy_version="stage6-sql-v1", cooldown_days=7, priority=priority,
                status="active", created_by=1,
                published_at=datetime.now(timezone.utc).replace(tzinfo=None),
            ))
        db.commit()
        result = recommendation_service.refresh(db, RecommendationRefreshRequest(
            target_date="2026-08-23", request_id="browser-stage6-refresh",
        ))
        print(json.dumps({
            "created": len(result["created_ids"]),
            "recommendations": db.scalar(select(func.count(Recommendation.id))) or 0,
            "external_calls": result["external_calls"],
        }, ensure_ascii=False))
    finally:
        db.close()
        set_current_tenant_id(None); set_current_owner_id(None); set_current_role(None)


if __name__ == "__main__":
    main()
