"""RBAC：owner / admin 角色权限校验（后端强制，fail closed）。

- owner：客户、套餐、账本、商品服务管理；只能查看 AI 运行状态；
- admin：AI 配置、提示词、RAG、测评、发布和回滚。
- require_owner / require_admin 默认从当前用户上下文取角色；
  缺少上下文时（生产环境）拒绝请求。
"""
from app.domain.errors import PermissionDeniedError

OWNER = "owner"
ADMIN = "admin"


def require_role(role: str | None, allowed: set[str]) -> None:
    if role not in allowed:
        raise PermissionDeniedError("无权限执行该操作")


def _resolve_role(role: str | None) -> str:
    if role is not None:
        return role
    from app.core.tenant import get_current_role

    return get_current_role()


def require_owner(role: str | None = None) -> None:
    """业务写操作需要 owner 权限（缺上下文 fail closed）。"""
    require_role(_resolve_role(role), {OWNER, ADMIN})


def require_admin(role: str | None = None) -> None:
    """AI 配置操作仅 admin（缺上下文 fail closed）。"""
    require_role(_resolve_role(role), {ADMIN})


def owner_can_manage_business(role: str | None) -> bool:
    return role in {OWNER, ADMIN}


def owner_can_manage_ai(role: str | None) -> bool:
    return role == ADMIN
