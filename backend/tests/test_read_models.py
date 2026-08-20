"""客户读模型测试：最后消费聚合、倒序、概览、服务详情。"""
from app.application import customer_read_service, ledger_service
from app.repositories import customers as customer_repo
from app.repositories import packages as package_repo
from app.repositories import services as service_repo
from app.schemas.ledger import LedgerEntryCreate


def test_last_consumption_and_sort(db_session):
    svc = service_repo.create_service(db_session, "面部清洁", "active")
    cust_a = customer_repo.create_customer(db_session, "小红", ["红姐"])
    cust_b = customer_repo.create_customer(db_session, "小黄", ["黄姐"])
    db_session.commit()

    ledger_service.create_ledger_entry(
        db_session, cust_a.id,
        LedgerEntryCreate(entry_type="one_time_service", service_id=svc.id, quantity=1, occurred_on="2026-08-20"),
    )

    summaries = customer_read_service.list_customer_summaries(db_session)
    assert summaries[0]["display_name"] == "小红"  # 有消费的排前面
    assert summaries[0]["last_consumed_service_name"] == "面部清洁"
    assert summaries[0]["last_consumed_at"] == "2026-08-20"
    assert summaries[1]["display_name"] == "小黄"
    assert summaries[1]["last_consumed_at"] is None


def test_purchase_does_not_change_last_consumption(db_session):
    svc = service_repo.create_service(db_session, "面部清洁", "active")
    cust = customer_repo.create_customer(db_session, "小红", ["红姐"])
    db_session.commit()

    # 购买套餐（不参与最后消费）
    package_repo.create_package(db_session, cust.id, svc.id, 5, 0, None, None)
    db_session.commit()

    summaries = customer_read_service.list_customer_summaries(db_session)
    assert summaries[0]["last_consumed_at"] is None  # 购买不覆盖最后消费


def test_product_purchase_does_not_change_last_consumption(db_session):
    svc = service_repo.create_service(db_session, "面部清洁", "active")
    cust = customer_repo.create_customer(db_session, "小红", ["红姐"])
    db_session.commit()

    ledger_service.create_ledger_entry(
        db_session, cust.id,
        LedgerEntryCreate(entry_type="product_purchase", product_name="面霜", quantity=1, occurred_on="2026-08-20"),
    )

    summaries = customer_read_service.list_customer_summaries(db_session)
    assert summaries[0]["last_consumed_at"] is None  # 商品购买不算消费
    assert summaries[0]["last_consumed_service_name"] is None


def test_overview_and_service_detail(db_session):
    svc = service_repo.create_service(db_session, "面部清洁", "active")
    cust = customer_repo.create_customer(db_session, "小红", ["红姐"])
    pkg = package_repo.create_package(db_session, cust.id, svc.id, 5, 0, None, None)
    db_session.commit()

    ledger_service.create_ledger_entry(
        db_session, cust.id,
        LedgerEntryCreate(entry_type="package_consumption", package_id=pkg.id, quantity=1, occurred_on="2026-08-19"),
    )

    overview = customer_read_service.get_customer_overview(db_session, cust.id)
    assert overview["service_type_count"] == 1
    assert overview["active_package_count"] == 1

    services = customer_read_service.list_customer_services(db_session, cust.id)
    assert services[0]["total_remaining_count"] == 4  # 5 - 1

    detail = customer_read_service.get_customer_service_detail(db_session, cust.id, svc.id)
    assert detail["packages"][0]["used_count"] == 1
    assert detail["packages"][0]["remaining_count"] == 4
    assert len(detail["history"]) == 1
