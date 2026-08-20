"""阶段3 确认写入测试：预检查、幂等、发生日期、多项统一回滚。"""
import pytest

from app.application import confirmation_service
from app.domain.errors import DomainError
from app.repositories import customers as customer_repo
from app.repositories import packages as package_repo
from app.repositories import proposals as proposal_repo
from app.repositories import services as service_repo
from app.schemas.agent import ConfirmRequest, PrecheckRequest


def _seed(db):
    svc = service_repo.create_service(db, "面部清洁", "active")
    cust = customer_repo.create_customer(db, "小红", ["红姐"])
    pkg = package_repo.create_package(db, cust.id, svc.id, 5, 0, None, None)
    db.commit()
    return svc, cust, pkg


def _proposal(db, text="测试"):
    prop = proposal_repo.create_proposal(db, text, "{}", 1, "pending")
    db.commit()
    return prop


def test_precheck_returns_balance_without_write(db_session):
    svc, cust, pkg = _seed(db_session)
    prop = _proposal(db_session)

    req = PrecheckRequest(customer={"customer_id": cust.id}, actions=[{"type": "consume_service", "service_id": svc.id, "quantity": 2}])
    out = confirmation_service.precheck(db_session, prop.id, req)

    assert out["ok"] is True
    assert out["actions"][0]["preview"]["used_after"] == 2
    assert out["actions"][0]["preview"]["remaining_count"] == 3
    assert package_repo.compute_used_count(db_session, pkg) == 0  # 未写入


def test_precheck_multiple_cards_returns_candidates(db_session):
    svc, cust, _ = _seed(db_session)
    package_repo.create_package(db_session, cust.id, svc.id, 5, 0, None, None)
    db_session.commit()
    prop = _proposal(db_session)

    req = PrecheckRequest(customer={"customer_id": cust.id}, actions=[{"type": "consume_service", "service_id": svc.id, "quantity": 1}])
    out = confirmation_service.precheck(db_session, prop.id, req)

    assert out["actions"][0]["ok"] is False
    assert len(out["actions"][0]["candidates"]) == 2


def test_confirm_idempotent(db_session):
    svc, cust, _ = _seed(db_session)
    prop = _proposal(db_session, "小红买面霜")
    req = ConfirmRequest(customer={"customer_id": cust.id}, actions=[{"type": "record_product_purchase", "product_name": "面霜", "quantity": 1}])

    out = confirmation_service.confirm(db_session, prop.id, req)
    assert out["status"] == "confirmed"
    assert proposal_repo.get_proposal(db_session, prop.id).confirmed_at is not None

    with pytest.raises(DomainError):
        confirmation_service.confirm(db_session, prop.id, req)


def test_confirm_records_occurred_on(db_session):
    svc, cust, _ = _seed(db_session)
    prop = _proposal(db_session, "核销")
    req = ConfirmRequest(
        customer={"customer_id": cust.id},
        actions=[{"type": "consume_service", "service_id": svc.id, "quantity": 1, "occurred_on": "2026-08-15"}],
    )
    out = confirmation_service.confirm(db_session, prop.id, req)
    assert out["results"][0]["occurred_on"] == "2026-08-15"


def test_multi_action_all_or_nothing(db_session):
    svc, cust, pkg = _seed(db_session)
    prop = _proposal(db_session, "多项操作")
    req = ConfirmRequest(
        customer={"customer_id": cust.id},
        actions=[
            {"type": "consume_service", "service_id": svc.id, "quantity": 1},
            {"type": "consume_service", "service_id": svc.id, "quantity": 10},  # 余额不足
        ],
    )
    with pytest.raises(DomainError):
        confirmation_service.confirm(db_session, prop.id, req)

    assert package_repo.compute_used_count(db_session, pkg) == 0  # 整组不写入
    assert proposal_repo.get_proposal(db_session, prop.id).status == "pending"


def test_confirm_creates_new_customer(db_session):
    svc, _, _ = _seed(db_session)
    prop = _proposal(db_session, "小黑买面霜")
    req = ConfirmRequest(
        customer={"new_customer": {"display_name": "小黑", "aliases": []}},
        actions=[{"type": "record_product_purchase", "product_name": "面霜", "quantity": 1}],
    )
    out = confirmation_service.confirm(db_session, prop.id, req)
    assert out["customer"]["display_name"] == "小黑"
    assert len(customer_repo.list_customers(db_session)) == 2
