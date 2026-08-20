"""阶段4回归测试：PRD 10 条表达的后端解析逻辑 + 异常与模型失败处理。

使用假适配器模拟“模型正确输出”，验证后端 enrich（客户匹配、服务匹配、操作拆分）。
真实模型解析质量已在阶段2/3人工核验，这里回归的是后端确定性逻辑。
"""
import json

from app.agent import agent_service
from app.infrastructure.llm.base import ModelError
from app.repositories import customers as customer_repo
from app.repositories import services as service_repo


class FakeAdapter:
    def __init__(self, response: str | None = None, raise_error: Exception | None = None):
        self.response = response
        self.raise_error = raise_error

    def chat(self, messages, temperature=0.0):
        if self.raise_error:
            raise self.raise_error
        return self.response


def _seed_full(db):
    for name in ["面部清洁", "肩颈按摩", "身体护理", "清痘", "脱毛"]:
        service_repo.create_service(db, name, "active")
    customer_repo.create_customer(db, "小红", ["红姐"])
    customer_repo.create_customer(db, "小黄", ["黄姐"])
    customer_repo.create_customer(db, "小蓝", ["蓝蓝"])
    db.commit()


def _interpret(db, text, customer_query, actions):
    raw = json.dumps(
        {
            "customer_query": customer_query,
            "customer_match": {"status": "not_found", "candidate_ids": [], "new_customer_name": None},
            "actions": actions,
            "needs_clarification": False,
            "clarification_question": None,
        },
        ensure_ascii=False,
    )
    return agent_service.interpret(db, text, adapter=FakeAdapter(raw))


def test_expr1_product_purchase(db_session):
    _seed_full(db_session)
    r = _interpret(db_session, "小红今天买了一盒面膜。", "小红", [{"type": "record_product_purchase", "product_name": "面膜", "quantity": 1}])
    assert r["error"] is None
    assert r["customer_match"]["status"] == "exact"
    assert r["actions"][0]["type"] == "record_product_purchase"


def test_expr2_consume_hair_removal(db_session):
    _seed_full(db_session)
    r = _interpret(db_session, "小黄今天脱毛一次。", "小黄", [{"type": "consume_service", "service_name": "脱毛", "quantity": 1}])
    assert r["actions"][0]["service_match"]["status"] == "exact"
    assert r["actions"][0]["service_match"]["resolved_service_id"] is not None


def test_expr3_shoulder_massage(db_session):
    _seed_full(db_session)
    r = _interpret(db_session, "小蓝今天肩颈按摩1次。", "小蓝", [{"type": "consume_service", "service_name": "肩颈按摩", "quantity": 1}])
    assert r["actions"][0]["service_match"]["candidates"][0]["name"] == "肩颈按摩"


def test_expr4_create_package(db_session):
    _seed_full(db_session)
    r = _interpret(db_session, "小蓝今天买了面部清洁5次。", "小蓝", [{"type": "create_package", "service_name": "面部清洁", "total_count": 5}])
    assert r["actions"][0]["type"] == "create_package"
    assert r["actions"][0]["total_count"] == 5


def test_expr5_fuzzy_query(db_session):
    _seed_full(db_session)
    r = _interpret(db_session, "给我瞅瞅红姐姐现在还有什么服务。", "红姐姐", [{"type": "query_customer"}])
    assert r["customer_match"]["status"] == "fuzzy"
    assert r["customer_match"]["candidates"][0]["display_name"] == "小红"


def test_expr6_face_to_facial_cleaning(db_session):
    _seed_full(db_session)
    r = _interpret(db_session, "小绿做了一次脸。", "小绿", [{"type": "consume_service", "service_name": "面部清洁", "quantity": 1}])
    assert r["customer_match"]["status"] == "not_found"
    assert r["customer_match"]["new_customer_name"] == "小绿"
    assert r["actions"][0]["service_match"]["candidates"][0]["name"] == "面部清洁"


def test_expr7_new_customer_product(db_session):
    _seed_full(db_session)
    r = _interpret(db_session, "小黑买了一个面霜。", "小黑", [{"type": "record_product_purchase", "product_name": "面霜", "quantity": 1}])
    assert r["customer_match"]["status"] == "not_found"
    assert r["actions"][0]["type"] == "record_product_purchase"


def test_expr8_split_four_actions(db_session):
    _seed_full(db_session)
    r = _interpret(
        db_session,
        "小蓝来店里本次做了面部清洁，清痘，做身体，本次额外买了面霜。",
        "小蓝",
        [
            {"type": "consume_service", "service_name": "面部清洁", "quantity": 1},
            {"type": "consume_service", "service_name": "清痘", "quantity": 1},
            {"type": "consume_service", "service_name": "身体护理", "quantity": 1},
            {"type": "record_product_purchase", "product_name": "面霜", "quantity": 1},
        ],
    )
    assert len(r["actions"]) == 4
    assert [a["type"] for a in r["actions"]] == ["consume_service", "consume_service", "consume_service", "record_product_purchase"]


def test_expr9_unknown_customer_consume(db_session):
    _seed_full(db_session)
    r = _interpret(db_session, "天天的肩颈卡今天又用了一次。", "天天", [{"type": "consume_service", "service_name": "肩颈按摩", "quantity": 1}])
    assert r["customer_match"]["status"] == "not_found"
    assert r["customer_match"]["new_customer_name"] == "天天"


def test_expr10_unknown_customer_query(db_session):
    _seed_full(db_session)
    r = _interpret(db_session, "小普好几天没来了，你给我看看他还有卡吗。", "小普", [{"type": "query_customer"}])
    assert r["customer_match"]["status"] == "not_found"
    assert r["actions"][0]["type"] == "query_customer"


def test_model_error_returns_sanitized_error(db_session):
    _seed_full(db_session)
    adapter = FakeAdapter(raise_error=ModelError("模型接口错误（HTTP 401）：无效密钥"))
    r = agent_service.interpret(db_session, "小红做面部清洁", adapter=adapter)
    assert r["error"] is not None
    assert r["status"] == "error"


def test_empty_input(db_session):
    r = agent_service.interpret(db_session, "   ")
    assert r["status"] == "error"
