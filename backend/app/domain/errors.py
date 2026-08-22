"""领域异常：用于把业务错误转换成可理解的中文提示。"""


class DomainError(Exception):
    """业务规则/参数错误，对应 HTTP 400。"""


class NotFoundError(Exception):
    """资源不存在，对应 HTTP 404。"""


class PermissionDeniedError(Exception):
    """权限不足，对应 HTTP 403。"""


class ConflictError(Exception):
    """可恢复的数据/并发冲突，对应 HTTP 409。"""

    def __init__(self, message: str, payload: dict | None = None):
        super().__init__(message)
        self.payload = payload or {}
