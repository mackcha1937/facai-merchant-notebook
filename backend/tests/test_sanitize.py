"""日志脱敏单元测试。"""
from app.core.logging import sanitize_text


def test_sanitize_replaces_secret():
    assert sanitize_text("token=abc123xyz", "abc123xyz") == "token=***"


def test_sanitize_bearer_header():
    out = sanitize_text("Authorization: Bearer sk-abcdefgh12345678")
    assert "sk-abcdefgh12345678" not in out


def test_sanitize_sk_style_key():
    out = sanitize_text("密钥是 sk-abcdefgh12345678 请勿泄露")
    assert "sk-abcdefgh12345678" not in out


def test_sanitize_api_key_assignment():
    out = sanitize_text("api_key=mysecretvalue")
    assert "mysecretvalue" not in out


def test_sanitize_keeps_normal_text():
    assert sanitize_text("普通日志内容") == "普通日志内容"
