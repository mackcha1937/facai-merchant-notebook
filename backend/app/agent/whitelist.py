"""操作白名单：Agent 只能提出这些操作，其余一律拒绝。

这是最终安全边界，提示词无法改变它。
"""
from app.domain.errors import DomainError

ALLOWED_ACTION_TYPES = {
    "create_package",
    "consume_service",
    "record_one_time_service",
    "record_product_purchase",
    "query_customer",
}


def ensure_allowed_action_types(actions) -> None:
    for action in actions:
        action_type = getattr(action, "type", None)
        if action_type not in ALLOWED_ACTION_TYPES:
            raise DomainError(f"模型提出了系统不允许的操作类型：{action_type}")
