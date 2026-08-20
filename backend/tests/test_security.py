"""安全相关测试：密钥不泄露、未确认不写库。"""
import json
import re
from pathlib import Path

from app.agent import agent_service
from app.repositories import customers as customer_repo
from app.repositories import packages as package_repo
from app.repositories import services as service_repo

BACKEND = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[2]


def test_frontend_source_has_no_api_key():
    """前端源码不得包含形如 sk-... 的真实密钥（变量名提示不算泄露）。"""
    frontend_src = ROOT / "frontend" / "src"
    key_pattern = re.compile(r"sk-[A-Za-z0-9_-]{8,}")
    for path in frontend_src.rglob("*.js*"):
        content = path.read_text(encoding="utf-8")
        assert not key_pattern.search(content), f"{path} 中出现疑似密钥"


def test_env_example_has_no_real_key():
    env_example = BACKEND / ".env.example"
    content = env_example.read_text(encoding="utf-8")
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("DEEPSEEK_API_KEY="):
            assert line == "DEEPSEEK_API_KEY="


class FakeAdapter:
    def chat(self, messages, temperature=0.0):
        return json.dumps(
            {
                "customer_query": "小红",
                "customer_match": {"status": "exact"},
                "actions": [{"type": "consume_service", "service_name": "面部清洁", "quantity": 1}],
                "needs_clarification": False,
                "clarification_question": None,
            },
            ensure_ascii=False,
        )


def test_unconfirmed_proposal_does_not_write(db_session):
    svc = service_repo.create_service(db_session, "面部清洁", "active")
    cust = customer_repo.create_customer(db_session, "小红", ["红姐"])
    package_repo.create_package(db_session, cust.id, svc.id, 5, 0, None, None)
    db_session.commit()

    before_customers = len(customer_repo.list_customers(db_session))
    before_packages = len(package_repo.list_packages_for_customer(db_session, cust.id))

    agent_service.interpret(db_session, "小红做面部清洁", adapter=FakeAdapter())

    assert len(customer_repo.list_customers(db_session)) == before_customers
    assert len(package_repo.list_packages_for_customer(db_session, cust.id)) == before_packages
    assert package_repo.get_package(db_session, package_repo.list_packages_for_customer(db_session, cust.id)[0].id).used_count == 0
