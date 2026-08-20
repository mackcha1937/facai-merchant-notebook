"""领域规则单元测试。"""
import pytest

from app.domain.errors import DomainError
from app.domain.rules import (
    remaining_count,
    validate_consume_quantity,
    validate_package_counts,
)


def test_remaining_count():
    assert remaining_count(10, 3) == 7


def test_total_must_be_positive():
    with pytest.raises(DomainError):
        validate_package_counts(0, 0)


def test_used_must_not_be_negative():
    with pytest.raises(DomainError):
        validate_package_counts(10, -1)


def test_used_cannot_exceed_total():
    with pytest.raises(DomainError):
        validate_package_counts(5, 6)


def test_valid_counts():
    total, used = validate_package_counts(9, 2)
    assert (total, used) == (9, 2)


def test_consume_zero_rejected():
    with pytest.raises(DomainError):
        validate_consume_quantity(10, 0, 0)


def test_consume_negative_rejected():
    with pytest.raises(DomainError):
        validate_consume_quantity(10, 0, -1)


def test_consume_exceeds_balance_rejected():
    with pytest.raises(DomainError):
        validate_consume_quantity(3, 2, 2)  # 2 + 2 > 3


def test_consume_ok():
    assert validate_consume_quantity(10, 3, 2) == 2
