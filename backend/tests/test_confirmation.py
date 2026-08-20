"""Proposal 确认写入测试（阶段3核心）。"""
import json

import pytest

from app.agent import agent_service
from app.application import confirmation_service
from app.domain.errors import DomainError
from app.repositories import customers as customer_repo
from app.repositories import packages as package_repo
from app.repositories import services as service_repo
from app.schemas.agent import ConfirmRequest


class FakeAdapter:
    def __init__(self, response: str):
        self.response = response

    def chat(self, messages, temperature=0.0):
        return self.response


def _seed(db):
    svc = service_repo.create_service(db, "面部清洁", "active")
    svc2 = service_repo.create_service(db, "脱毛", "active")
    cust = customer_repo.create_customer(db, "小红", ["红姐"])
    db.commit()
    return svc, svc2, cust


def _interpret(db, raw, text):
    return agent_service.interpret(db, text, adapter=FakeAdapter(raw))


def _output(customer_query="小红", actions=None, status="exact"):
    return json.dumps(
        {
            "customer_query": customer_query,
            "customer_match": {"status": status, "candidate_ids": [], "new_customer_name": None},
            "actions": actions or [],
            "needs_clarification": False,
            "clarification_question": None,
        },
        ensure_ascii=False,
    )


def _req(customer_id=None, new_customer=None, actions=None):
    return ConfirmRequest(
        customer={"customer_id": customer_id, "new_customer": new_customer},
        actions=actions or [],
    )


def test_confirm_create_package(db_session):
    svc, _, cust = _seed(db_session)
    raw = _output(actions=[{"type": "create_package", "service_name": "面部清洁", "total_count": 5}])
    pid = _interpret(db_session, raw, "小红买面部清洁5次")["id"]

    out = confirmation_service.confirm(
        db_session, pid, _req(customer_id=cust.id, actions=[{"type": "create_package", "service_id": svc.id, "total_count": 5}])
    )
    assert out["status"] == "confirmed"
    assert out["results"][0]["message"].startswith("已创建套餐")

    pkgs = package_repo.list_packages_for_customer(db_session, cust.id)
    assert len(pkgs) == 1
    assert pkgs[0].total_count == 5
    assert package_repo.compute_used_count(db_session, pkgs[0]) == 0


def test_confirm_consume_single_card(db_session):
    svc, _, cust = _seed(db_session)
    pkg = package_repo.create_package(db_session, cust.id, svc.id, 5, 0, None, None)
    db_session.commit()

    raw = _output(actions=[{"type": "consume_service", "service_name": "面部清洁", "quantity": 2}])
    pid = _interpret(db_session, raw, "小红做面部清洁2次")["id"]

    out = confirmation_service.confirm(
        db_session, pid, _req(customer_id=cust.id, actions=[{"type": "consume_service", "service_id": svc.id, "quantity": 2}])
    )
    assert "已累计使用 2/5 次，还剩 3 次" in out["results"][0]["message"]
    assert package_repo.compute_used_count(db_session, package_repo.get_package(db_session, pkg.id)) == 2


def test_consume_insufficient_balance_rejected(db_session):
    svc, _, cust = _seed(db_session)
    package_repo.create_package(db_session, cust.id, svc.id, 3, 3, None, None)
    db_session.commit()

    raw = _output(actions=[{"type": "consume_service", "service_name": "面部清洁", "quantity": 1}])
    pid = _interpret(db_session, raw, "小红做面部清洁")["id"]

    with pytest.raises(DomainError) as exc:
        confirmation_service.confirm(
            db_session, pid, _req(customer_id=cust.id, actions=[{"type": "consume_service", "service_id": svc.id, "quantity": 1}])
        )
    assert "余额不足" in str(exc.value)


def test_consume_no_package_rejected(db_session):
    svc, _, cust = _seed(db_session)
    raw = _output(actions=[{"type": "consume_service", "service_name": "面部清洁", "quantity": 1}])
    pid = _interpret(db_session, raw, "小红做面部清洁")["id"]

    with pytest.raises(DomainError) as exc:
        confirmation_service.confirm(
            db_session, pid, _req(customer_id=cust.id, actions=[{"type": "consume_service", "service_id": svc.id, "quantity": 1}])
        )
    assert "没有" in str(exc.value)


def test_consume_multiple_cards_requires_selection(db_session):
    svc, _, cust = _seed(db_session)
    p1 = package_repo.create_package(db_session, cust.id, svc.id, 5, 0, None, None)
    package_repo.create_package(db_session, cust.id, svc.id, 5, 0, None, None)
    db_session.commit()

    raw = _output(actions=[{"type": "consume_service", "service_name": "面部清洁", "quantity": 1}])
    pid = _interpret(db_session, raw, "小红做面部清洁")["id"]

    # 不指定卡 → 报错
    with pytest.raises(DomainError) as exc:
        confirmation_service.confirm(
            db_session, pid, _req(customer_id=cust.id, actions=[{"type": "consume_service", "service_id": svc.id, "quantity": 1}])
        )
    assert "多张" in str(exc.value)

    # 指定卡 → 成功
    out = confirmation_service.confirm(
        db_session, pid,
        _req(customer_id=cust.id, actions=[{"type": "consume_service", "service_id": svc.id, "quantity": 1, "package_id": p1.id}]),
    )
    assert out["status"] == "confirmed"
    assert package_repo.compute_used_count(db_session, package_repo.get_package(db_session, p1.id)) == 1


def test_one_time_service_does_not_change_package(db_session):
    svc, _, cust = _seed(db_session)
    pkg = package_repo.create_package(db_session, cust.id, svc.id, 5, 1, None, None)
    db_session.commit()

    raw = _output(actions=[{"type": "record_one_time_service", "service_name": "面部清洁", "quantity": 1}])
    pid = _interpret(db_session, raw, "小红做了一次面部清洁")["id"]

    out = confirmation_service.confirm(
        db_session, pid, _req(customer_id=cust.id, actions=[{"type": "record_one_time_service", "service_id": svc.id, "quantity": 1}])
    )
    assert "已消费 1 次 面部清洁 服务" in out["results"][0]["message"]
    assert package_repo.compute_used_count(db_session, package_repo.get_package(db_session, pkg.id)) == 1  # 未变


def test_product_purchase(db_session):
    _, _, cust = _seed(db_session)
    raw = _output(actions=[{"type": "record_product_purchase", "product_name": "面霜", "quantity": 1}])
    pid = _interpret(db_session, raw, "小红买了一个面霜")["id"]

    out = confirmation_service.confirm(
        db_session, pid, _req(customer_id=cust.id, actions=[{"type": "record_product_purchase", "product_name": "面霜", "quantity": 1}])
    )
    assert "面霜" in out["results"][0]["message"]


def test_confirm_creates_new_customer(db_session):
    svc, _, cust = _seed(db_session)
    raw = _output(
        customer_query="小黑",
        status="not_found",
        actions=[{"type": "record_product_purchase", "product_name": "面霜", "quantity": 1}],
    )
    pid = _interpret(db_session, raw, "小黑买了一个面霜")["id"]

    out = confirmation_service.confirm(
        db_session, pid,
        _req(new_customer={"display_name": "小黑", "aliases": []}, actions=[{"type": "record_product_purchase", "product_name": "面霜", "quantity": 1}]),
    )
    assert out["customer"]["display_name"] == "小黑"
    assert len(customer_repo.list_customers(db_session)) == 2


def test_query_customer_returns_summary(db_session):
    svc, _, cust = _seed(db_session)
    package_repo.create_package(db_session, cust.id, svc.id, 5, 2, None, None)
    db_session.commit()

    raw = _output(actions=[{"type": "query_customer"}])
    pid = _interpret(db_session, raw, "红姐还有什么服务")["id"]

    out = confirmation_service.confirm(
        db_session, pid, _req(customer_id=cust.id, actions=[{"type": "query_customer"}])
    )
    q = out["results"][0]
    assert q["type"] == "query_customer"
    assert q["customer"]["packages"][0]["remaining_count"] == 3


def test_cannot_confirm_twice(db_session):
    svc, _, cust = _seed(db_session)
    raw = _output(actions=[{"type": "record_product_purchase", "product_name": "面霜", "quantity": 1}])
    pid = _interpret(db_session, raw, "小红买面霜")["id"]
    req = _req(customer_id=cust.id, actions=[{"type": "record_product_purchase", "product_name": "面霜", "quantity": 1}])
    confirmation_service.confirm(db_session, pid, req)

    with pytest.raises(DomainError):
        confirmation_service.confirm(db_session, pid, req)


def test_invalid_action_type_rejected(db_session):
    _, _, cust = _seed(db_session)
    raw = _output(actions=[{"type": "query_customer"}])
    pid = _interpret(db_session, raw, "查询")["id"]
    with pytest.raises(DomainError):
        confirmation_service.confirm(
            db_session, pid, _req(customer_id=cust.id, actions=[{"type": "delete_customer"}])
        )
