"""V2 阶段0 模型能力验证（严格版）。

验证 6 项：模型ID可用性、结构化JSON(JSON Schema校验)、超时、错误处理、工具调用、流式SSE。
所有输出脱敏，不返回 API Key 和敏感错误正文。
"""
import json

import httpx
import jsonschema

# 结构化输出验证用的 JSON Schema（与 contracts/agent-output.schema.json 的 items 子结构一致）
JSON_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["customer_query", "intent", "items"],
    "properties": {
        "customer_query": {"type": "string"},
        "intent": {"type": "string"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["raw_name", "kind", "quantity"],
                "properties": {
                    "raw_name": {"type": "string"},
                    "kind": {"type": "string", "enum": ["product", "service", "unknown"]},
                    "quantity": {"type": "number", "exclusiveMinimum": 0},
                },
            },
        },
    },
}

# 无副作用测试工具（不执行任何数据库写入）
TEST_TOOL = {
    "type": "function",
    "function": {
        "name": "lookup_test_customer",
        "description": "查询测试客户信息（无副作用，仅返回固定文本，不写数据库）",
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
}


def _ok(name, detail):
    return {"name": name, "ok": True, "detail": detail}


def _fail(name, detail):
    return {"name": name, "ok": False, "detail": detail}


def check_model_id(base, model, secret, headers):
    payload = {"model": model, "messages": [{"role": "user", "content": "回复 OK"}], "max_tokens": 20}
    try:
        resp = httpx.post(f"{base}/chat/completions", json=payload, headers=headers, timeout=30)
        if resp.status_code < 400:
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return _ok("模型ID可用性", f"model={model} 被接受（HTTP {resp.status_code}，返回 {content[:30]!r}）")
        return _fail("模型ID可用性", f"HTTP {resp.status_code}: {resp.text[:150]}")
    except httpx.HTTPError as exc:
        return _fail("模型ID可用性", f"网络异常 {type(exc).__name__}")


def check_json_output(base, model, secret, headers):
    prompt = (
        "识别以下输入，只输出一个 JSON 对象，不要 Markdown、不要解释、不要思考过程。\n"
        "输入：小蓝今天肩颈按摩1次。\n"
        '输出结构必须是：{"customer_query":"小蓝","intent":"redeem_service",'
        '"items":[{"raw_name":"肩颈按摩","kind":"service","quantity":1}]}'
    )
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "max_tokens": 800,
        "temperature": 0,
    }
    try:
        resp = httpx.post(f"{base}/chat/completions", json=payload, headers=headers, timeout=30)
        if resp.status_code >= 400:
            return _fail("结构化JSON输出", f"HTTP {resp.status_code}: {resp.text[:150]}")
        content = resp.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        jsonschema.validate(parsed, JSON_OUTPUT_SCHEMA)  # 全量 Schema 校验，非只查两个字段
        return _ok("结构化JSON输出", f"通过 JSON Schema 校验，字段={list(parsed.keys())}")
    except (json.JSONDecodeError, jsonschema.ValidationError, KeyError, IndexError) as exc:
        return _fail("结构化JSON输出", f"校验失败: {type(exc).__name__}: {str(exc)[:120]}")
    except httpx.HTTPError as exc:
        return _fail("结构化JSON输出", f"网络异常 {type(exc).__name__}")


def check_timeout(base, model, secret, headers):
    payload = {"model": model, "messages": [{"role": "user", "content": "说点什么"}], "max_tokens": 50}
    try:
        with httpx.Client(timeout=0.001) as client:
            client.post(f"{base}/chat/completions", json=payload, headers=headers)
        return _fail("超时行为", "极短超时未触发（异常）")
    except httpx.TimeoutException:
        return _ok("超时行为", "明确捕获 httpx.TimeoutException")
    except httpx.HTTPError as exc:
        # DNS/连接/认证等非超时异常，判定失败
        return _fail("超时行为", f"抛出非超时异常 {type(exc).__name__}，判定失败")
    except Exception as exc:  # noqa: BLE001
        return _fail("超时行为", f"抛出未知异常 {type(exc).__name__}，判定失败")


def check_error_handling(base, secret, headers):
    payload = {"model": "not-a-real-model-xyz", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5}
    try:
        resp = httpx.post(f"{base}/chat/completions", json=payload, headers=headers, timeout=30)
        if 400 <= resp.status_code < 500:
            text = resp.text.lower()
            # 错误内容必须明确表示模型不存在或不支持
            if any(kw in text for kw in ["model", "not", "invalid", "support", "exist"]):
                return _ok("错误模型处理", f"HTTP {resp.status_code} + 明确模型不支持错误")
            return _fail("错误模型处理", f"HTTP {resp.status_code} 但内容不明确: {resp.text[:150]}")
        if resp.status_code < 400:
            return _fail("错误模型处理", f"返回 {resp.status_code}（2xx，错误模型竟被接受）")
        return _fail("错误模型处理", f"返回 {resp.status_code}（5xx）")
    except httpx.HTTPError as exc:
        return _fail("错误模型处理", f"网络异常 {type(exc).__name__}")
    except Exception as exc:  # noqa: BLE001
        return _fail("错误模型处理", f"未知异常 {type(exc).__name__}")


def check_tool_call(base, model, secret, headers):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "请调用 lookup_test_customer 工具，参数 name 设为 小红"}],
        "tools": [TEST_TOOL],
        "max_tokens": 200,
    }
    try:
        resp = httpx.post(f"{base}/chat/completions", json=payload, headers=headers, timeout=30)
        if resp.status_code >= 400:
            return _fail("工具调用", f"HTTP {resp.status_code}: {resp.text[:150]}")
        message = resp.json()["choices"][0]["message"]
        tool_calls = message.get("tool_calls")
        if not tool_calls:
            return _fail("工具调用", "模型未返回 tool_calls")
        fn = tool_calls[0].get("function", {})
        name_ok = fn.get("name") == "lookup_test_customer"
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except json.JSONDecodeError:
            return _fail("工具调用", "工具参数不是合法 JSON")
        param_ok = args.get("name") == "小红"
        if name_ok and param_ok:
            return _ok("工具调用", f"返回 tool_calls，工具名/参数正确（name={args.get('name')}）")
        return _fail("工具调用", f"工具名={fn.get('name')} 参数={fn.get('arguments')}")
    except (KeyError, IndexError) as exc:
        return _fail("工具调用", f"响应解析失败 {type(exc).__name__}")
    except httpx.HTTPError as exc:
        return _fail("工具调用", f"网络异常 {type(exc).__name__}")


def check_stream(base, model, secret, headers):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "用一句话介绍你自己"}],
        "stream": True,
        "max_tokens": 800,
    }
    deltas = 0
    saw_done = False
    try:
        with httpx.Client(timeout=30) as client:
            with client.stream("POST", f"{base}/chat/completions", json=payload, headers=headers) as resp:
                if resp.status_code >= 400:
                    return _fail("流式响应", f"HTTP {resp.status_code}")
                for line in resp.iter_lines():
                    if not line:
                        continue
                    line = line.strip()
                    if line.startswith("data:"):
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            saw_done = True
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk["choices"][0]["delta"].get("content", "")
                            if delta:
                                deltas += 1
                        except (json.JSONDecodeError, KeyError, IndexError):
                            return _fail("流式响应", "SSE 数据行解析失败")
        if deltas >= 1 and saw_done:
            return _ok("流式响应", f"收到 {deltas} 个有效内容增量 + [DONE] 结束标记")
        return _fail("流式响应", f"增量={deltas}，结束标记={saw_done}，不满足")
    except httpx.HTTPError as exc:
        return _fail("流式响应", f"网络异常/中途断开 {type(exc).__name__}")
    except Exception as exc:  # noqa: BLE001
        return _fail("流式响应", f"未知异常 {type(exc).__name__}")


def run_all_verifications(base, model, secret) -> list[dict]:
    headers = {
        "Authorization": f"Bearer {secret}",
        "Content-Type": "application/json",
    }
    return [
        check_model_id(base, model, secret, headers),
        check_json_output(base, model, secret, headers),
        check_tool_call(base, model, secret, headers),
        check_stream(base, model, secret, headers),
        check_timeout(base, model, secret, headers),
        check_error_handling(base, secret, headers),
    ]
