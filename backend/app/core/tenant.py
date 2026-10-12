"""租户与当前用户上下文（fail closed）。

- 禁止 ContextVar 静默默认 tenant=1：缺少上下文时按 fail closed 处理；
- 正式登录未实现前，允许服务端配置的本地默认 owner（仅开发环境）；
- 不接受客户端任意传入 X-Tenant-ID 或角色冒充。
"""
from contextvars import ContextVar

from app.core.config import get_settings
from app.domain.errors import DomainError

_current_tenant_id: ContextVar[int | None] = ContextVar("current_tenant_id", default=None)
_current_user_role: ContextVar[str | None] = ContextVar("current_user_role", default=None)
_current_user_id: ContextVar[int | None] = ContextVar("current_user_id", default=None)


def get_current_tenant_id() -> int:
    tid = _current_tenant_id.get()
    if tid is not None:
        return tid
    settings = get_settings()
    if settings.local_dev_owner_enabled:
        return settings.local_default_tenant_id
    raise DomainError("缺少租户上下文，拒绝业务请求")


def get_current_role() -> str:
    role = _current_user_role.get()
    if role is not None:
        return role
    settings = get_settings()
    if settings.local_dev_owner_enabled:
        return settings.local_default_owner_role
    raise DomainError("缺少用户上下文，拒绝请求")


def get_current_owner_id() -> int:
    user_id = _current_user_id.get()
    if user_id is not None:
        return user_id
    settings = get_settings()
    if settings.local_dev_owner_enabled:
        return settings.local_default_owner_id
    raise DomainError("缺少用户上下文，拒绝请求")


def set_current_tenant_id(tenant_id: int | None):
    return _current_tenant_id.set(tenant_id)


def set_current_role(role: str | None):
    return _current_user_role.set(role)


def set_current_owner_id(owner_id: int | None):
    return _current_user_id.set(owner_id)


def reset_current_tenant_id(token) -> None:
    _current_tenant_id.reset(token)


def reset_current_role(token) -> None:
    _current_user_role.reset(token)


def reset_current_owner_id(token) -> None:
    _current_user_id.reset(token)
