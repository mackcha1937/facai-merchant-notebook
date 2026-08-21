"""RBAC：owner / admin 角色权限校验（后端强制，非仅前端隐藏）。

- owner：客户、套餐、账本、商品服务管理；只能查看 AI 运行状态；
- admin：AI 配置、提示词、RAG、测评、发布和回滚。
"""
from app.domain.errors import DomainError

OWNER = "owner"
ADMIN = "admin"


def require_role(role: str | None, allowed: set[str]) -> None:
    if role not in allowed:
        raise DomainError("无权限执行该操作")


def require_owner(role: str | None) -> None:
    """业务写操作需要 owner 权限。"""
    require_role(role, {OWNER, ADMIN})


def require_admin(role: str | None) -> None:
    """AI 配置操作仅 admin。"""
    require_role(role, {ADMIN})


def owner_can_manage_business(role: str | None) -> bool:
    return role in {OWNER, ADMIN}


def owner_can_manage_ai(role: str | None) -> bool:
    return role == ADMIN
