"""Agent interpret 用例测试（使用假适配器，不依赖真实网络）。"""
import json

from app.agent import agent_service
from app.repositories import customers as customer_repo
from app.repositories import services as service_repo


class FakeAdapter:
    def __init__(self, response: str):
        self.response = response

    def chat(self, messages, temperature=0.0):
        return self.response


def _seed(db):
    svc = service_repo.create_service(db, "面部清洁", "active")
    cust = customer_repo.create_customer(db, "小红", ["红姐"])
    db.commit()
    return svc, cust


def _output(**overrides):
    data = {
        "customer_query": "小红",
        "customer_match": {"status": "exact", "candidate_ids": [], "new_customer_name": None},
        "actions": [{"type": "consume_service", "service_name": "面部清洁", "quantity": 1}],
        "needs_clarification": False,
        "clarification_question": None,
    }
    data.update(overrides)
    return json.dumps(data, ensure_ascii=False)


def test_interpret_ok(db_session):
    _seed(db_session)
    result = agent_service.interpret(db_session, "小红做面部清洁", adapter=FakeAdapter(_output()))
    assert result["error"] is None
    assert result["status"] == "pending"
    assert result["write_allowed"] is False
    assert result["customer_match"]["status"] == "exact"
    assert result["actions"][0]["service_match"]["status"] == "exact"


def test_interpret_rejects_forbidden_action(db_session):
    _seed(db_session)
    raw = json.dumps(
        {"customer_query": "小红", "actions": [{"type": "delete_customer"}]},
        ensure_ascii=False,
    )
    result = agent_service.interpret(db_session, "删除小红", adapter=FakeAdapter(raw))
    assert result["error"] is not None
    assert "不允许" in result["error"]


def test_interpret_bad_json(db_session):
    _seed(db_session)
    result = agent_service.interpret(db_session, "测试", adapter=FakeAdapter("这不是JSON"))
    assert result["error"] is not None


def test_interpret_new_customer(db_session):
    _seed(db_session)
    raw = json.dumps(
        {
            "customer_query": "小黑",
            "customer_match": {"status": "not_found", "candidate_ids": [], "new_customer_name": "小黑"},
            "actions": [{"type": "record_product_purchase", "product_name": "面霜", "quantity": 1}],
            "needs_clarification": False,
            "clarification_question": None,
        },
        ensure_ascii=False,
    )
    result = agent_service.interpret(db_session, "小黑买了一个面霜", adapter=FakeAdapter(raw))
    assert result["customer_match"]["status"] == "not_found"
    assert result["customer_match"]["new_customer_name"] == "小黑"


def test_interpret_does_not_write(db_session):
    _seed(db_session)
    agent_service.interpret(db_session, "小红做面部清洁", adapter=FakeAdapter(_output()))
    # 阶段2不应产生任何业务写入：客户仍只有1位，套餐0张，记录0条
    customers = customer_repo.list_customers(db_session)
    assert len(customers) == 1
