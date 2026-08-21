"""租户上下文：所有仓储查询强制带 tenant_id。

本地 MVP 默认租户 id=1；未来多租户通过 ContextVar 注入当前租户。
禁止先按对象 ID 查询再在应用层判断租户。
"""
from contextvars import ContextVar

DEFAULT_TENANT_ID = 1

_current_tenant_id: ContextVar[int] = ContextVar("current_tenant_id", default=DEFAULT_TENANT_ID)


def get_current_tenant_id() -> int:
    return _current_tenant_id.get()


def set_current_tenant_id(tenant_id: int):
    return _current_tenant_id.set(tenant_id)
