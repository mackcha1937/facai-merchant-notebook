"""客户与服务模糊匹配测试。"""
from app.agent.matching import match_customers, match_services


def test_customer_fuzzy_match_by_alias():
    customers = [
        {"id": 1, "display_name": "小红", "aliases": ["红姐"]},
        {"id": 2, "display_name": "小黄", "aliases": ["黄姐"]},
    ]
    matches = match_customers("红姐姐", customers)
    assert matches
    assert matches[0]["id"] == 1


def test_customer_exact_alias():
    customers = [{"id": 1, "display_name": "小红", "aliases": ["红姐"]}]
    matches = match_customers("红姐", customers)
    assert matches[0]["match_type"] == "exact"


def test_customer_limit_three():
    customers = [
        {"id": i, "display_name": f"小{i}", "aliases": []} for i in range(10)
    ]
    matches = match_customers("小", customers, limit=3)
    assert len(matches) == 3


def test_service_contains_match():
    services = [{"id": 1, "name": "面部清洁"}, {"id": 2, "name": "脱毛"}]
    matches = match_services("面部", services)
    assert matches[0]["id"] == 1


def test_service_no_match():
    services = [{"id": 1, "name": "面部清洁"}]
    matches = match_services("完全不相关", services)
    assert matches == []
