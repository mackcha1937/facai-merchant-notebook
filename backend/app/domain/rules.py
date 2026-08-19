"""领域规则：不可绕过的业务约束，与数据库无关。

这些规则是最终防线，任何写入都必须经过这里校验，
不能只依赖系统提示词或前端。
"""
from app.domain.errors import DomainError


def ensure_positive_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise DomainError(f"{field_name}必须是正整数")
    return value


def ensure_non_negative_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise DomainError(f"{field_name}不能为负数")
    return value


def remaining_count(total_count: int, used_count: int) -> int:
    """权威余额：剩余次数 = 总次数 - 已用次数。"""
    return total_count - used_count


def validate_package_counts(total_count: int, used_count: int) -> tuple[int, int]:
    total = ensure_positive_int(total_count, "总次数")
    used = ensure_non_negative_int(used_count, "已用次数")
    if used > total:
        raise DomainError("已用次数不能超过总次数")
    return total, used


def validate_consume_quantity(package_total: int, package_used: int, quantity) -> int:
    """核销校验：数量为正整数，且不能使余额为负。"""
    q = ensure_positive_int(quantity, "核销数量")
    if package_used + q > package_total:
        raise DomainError("余额不足，无法核销")
    return q


def validate_display_name(name) -> str:
    if name is None or not str(name).strip():
        raise DomainError("客户化名不能为空")
    return str(name).strip()


def validate_service_name(name) -> str:
    if name is None or not str(name).strip():
        raise DomainError("服务名称不能为空")
    return str(name).strip()
