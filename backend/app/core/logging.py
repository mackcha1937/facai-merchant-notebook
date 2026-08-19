"""日志脱敏：过滤 API Key、Authorization 头等敏感信息。

规则：
- 若日志文本中出现配置的 API Key，替换为 ***
- 匹配 Authorization: Bearer ... / api_key=... 等形式
- 匹配形如 sk-... 的常见密钥格式
"""
import logging
import re

_API_KEY_PATTERNS = [
    re.compile(r"(?i)(authorization\s*[:=]\s*Bearer\s+)[^\s,;]+"),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
]


def sanitize_text(value, secret=None):
    """对任意文本做脱敏，返回安全文本。"""
    if value is None:
        return None
    text = str(value)
    if secret:
        text = text.replace(secret, "***")
    for pattern in _API_KEY_PATTERNS:
        text = pattern.sub(lambda m: (m.group(1) + "***") if m.groups() else "***", text)
    return text


class SanitizingFilter(logging.Filter):
    """挂在日志 logger 上的过滤器，写入前脱敏。"""

    def __init__(self, secret_provider=None):
        super().__init__()
        self._secret_provider = secret_provider

    def _secret(self):
        try:
            if self._secret_provider:
                return self._secret_provider()
        except Exception:
            pass
        return None

    def filter(self, record):
        secret = self._secret()
        try:
            record.msg = sanitize_text(record.msg, secret)
        except Exception:
            pass
        try:
            if isinstance(record.args, dict):
                record.args = {
                    k: (sanitize_text(v, secret) if isinstance(v, str) else v)
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    (sanitize_text(a, secret) if isinstance(a, str) else a)
                    for a in record.args
                )
        except Exception:
            pass
        return True
