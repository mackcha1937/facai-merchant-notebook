"""操作白名单测试。"""
import pytest

from app.agent.schema import AgentOutput
from app.agent.whitelist import ALLOWED_ACTION_TYPES, ensure_allowed_action_types
from app.domain.errors import DomainError


def test_whitelist_contains_five_types():
    assert ALLOWED_ACTION_TYPES == {
        "create_package",
        "consume_service",
        "record_one_time_service",
        "record_product_purchase",
        "query_customer",
    }


def test_allowed_action_passes():
    output = AgentOutput(actions=[{"type": "consume_service"}])
    ensure_allowed_action_types(output.actions)


def test_forbidden_action_rejected():
    output = AgentOutput(actions=[{"type": "delete_customer"}])
    with pytest.raises(DomainError):
        ensure_allowed_action_types(output.actions)
