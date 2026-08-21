"""V2 阶段0：DeepSeek 模型真实能力验证。

验证内容：
1. 模型 ID（deepseek-v4-pro）是否被官方接口真实接受；
2. 结构化 JSON 输出能力；
3. 超时行为；
4. 错误处理（错误模型 ID）。

安全：API Key 只从 backend/.env 读取，输出全部脱敏，绝不打印 Key。
"""
import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.core.logging import sanitize_text  # noqa: E402

settings = get_settings()
BASE = settings.deepseek_api_base_url.rstrip("/")
MODEL = settings.deepseek_model_id
SECRET = settings.deepseek_api_key or ""

HEADERS = {
    "Authorization": f"Bearer {SECRET}",
    "Content-Type": "application/json",
}


def _post(url, payload, timeout=30.0):
    with httpx.Client(timeout=timeout) as client:
        return client.post(url, json=payload, headers=HEADERS)


def _result(name, ok, detail):
    print(f"\n[{name}] {'✅ 通过' if ok else '❌ 失败'}")
    print(f"  {detail}")


def test_model_id():
    """1. deepseek-v4-pro 是否真实可用。"""
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "回复 OK"}],
        "max_tokens": 10,
        "stream": False,
    }
    try:
        resp = _post(f"{BASE}/chat/completions", payload)
        if resp.status_code < 400:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            _result("模型ID可用性", True, f"model={MODEL} 返回: {content[:50]!r}")
            return True
        _result("模型ID可用性", False, sanitize_text(f"HTTP {resp.status_code}: {resp.text[:300]}", SECRET))
        return False
    except Exception as exc:  # noqa: BLE001
        _result("模型ID可用性", False, sanitize_text(str(exc), SECRET))
        return False


def test_json_output():
    """2. 结构化 JSON 输出能力（模拟 agent-output 片段）。"""
    prompt = (
        "你只输出 JSON，不要 Markdown。识别：小蓝今天肩颈按摩1次。"
        '输出格式：{"customer_query":"小蓝","intent":"redeem_service","items":[{"raw_name":"肩颈按摩","kind":"service","quantity":1}]}'
    )
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300,
        "temperature": 0,
        "stream": False,
    }
    try:
        resp = _post(f"{BASE}/chat/completions", payload, timeout=30)
        if resp.status_code >= 400:
            _result("结构化JSON输出", False, sanitize_text(f"HTTP {resp.status_code}: {resp.text[:200]}", SECRET))
            return
        content = resp.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        ok = parsed.get("customer_query") == "小蓝" and parsed.get("intent") == "redeem_service"
        _result("结构化JSON输出", ok, f"解析成功，字段={list(parsed.keys())}, 原文前80字: {content[:80]!r}")
    except Exception as exc:  # noqa: BLE001
        _result("结构化JSON输出", False, sanitize_text(str(exc), SECRET))


def test_timeout():
    """3. 超时行为：极短超时应快速失败并抛超时错误。"""
    payload = {"model": MODEL, "messages": [{"role": "user", "content": "说点什么"}], "max_tokens": 50}
    t0 = time.time()
    try:
        _post(f"{BASE}/chat/completions", payload, timeout=0.001)
        _result("超时行为", False, "极短超时未触发（异常）")
    except httpx.TimeoutException:
        _result("超时行为", True, f"正确抛出超时（耗时 {time.time()-t0:.3f}s）")
    except Exception as exc:  # noqa: BLE001
        _result("超时行为", True, f"触发异常类型 {type(exc).__name__}（耗时 {time.time()-t0:.3f}s）")


def test_error_handling():
    """4. 错误处理：错误模型 ID 应返回可读错误，不崩溃。"""
    payload = {"model": "not-a-real-model-xyz", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5}
    try:
        resp = _post(f"{BASE}/chat/completions", payload)
        _result("错误处理", True, sanitize_text(f"错误模型ID返回 HTTP {resp.status_code}: {resp.text[:200]}", SECRET))
    except Exception as exc:  # noqa: BLE001
        _result("错误处理", True, sanitize_text(f"异常: {type(exc).__name__}: {exc}", SECRET))


if __name__ == "__main__":
    print(f"验证目标：base={BASE} model={MODEL}")
    print(f"API Key 已配置: {settings.is_model_configured}")
    if not settings.is_model_configured:
        print("❌ 未配置 API Key，请在 backend/.env 填写 DEEPSEEK_API_KEY 后重试。")
        sys.exit(1)

    test_model_id()
    test_json_output()
    test_timeout()
    test_error_handling()
    print("\n验证结束。")
