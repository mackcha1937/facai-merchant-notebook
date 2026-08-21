"""V2 阶段0：模型能力验证接口（返回脱敏结果，不返回 API Key）。"""
import json
import time

import httpx
from fastapi import APIRouter

from app.core.config import get_settings
from app.core.logging import sanitize_text

router = APIRouter(prefix="/api/v2/stage0", tags=["v2-stage0"])


def _check_model_id(base, model, secret, headers):
    payload = {"model": model, "messages": [{"role": "user", "content": "回复 OK"}], "max_tokens": 10}
    try:
        resp = httpx.post(f"{base}/chat/completions", json=payload, headers=headers, timeout=30)
        if resp.status_code < 400:
            return {"name": "模型ID可用性", "ok": True, "detail": f"model={model} 被接口接受（HTTP {resp.status_code}）"}
        return {"name": "模型ID可用性", "ok": False, "detail": sanitize_text(f"HTTP {resp.status_code}: {resp.text[:200]}", secret)}
    except Exception as exc:  # noqa: BLE001
        return {"name": "模型ID可用性", "ok": False, "detail": sanitize_text(str(exc), secret)}


def _check_json(base, model, secret, headers):
    prompt = (
        "你只输出 JSON，不要 Markdown。识别：小蓝今天肩颈按摩1次。"
        '输出格式：{"customer_query":"小蓝","intent":"redeem_service","items":[{"raw_name":"肩颈按摩","kind":"service","quantity":1}]}'
    )
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 300, "temperature": 0}
    try:
        resp = httpx.post(f"{base}/chat/completions", json=payload, headers=headers, timeout=30)
        if resp.status_code >= 400:
            return {"name": "结构化JSON输出", "ok": False, "detail": sanitize_text(f"HTTP {resp.status_code}", secret)}
        content = resp.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        ok = parsed.get("customer_query") == "小蓝" and parsed.get("intent") == "redeem_service"
        return {"name": "结构化JSON输出", "ok": ok, "detail": f"解析成功，字段={list(parsed.keys())}"}
    except Exception as exc:  # noqa: BLE001
        return {"name": "结构化JSON输出", "ok": False, "detail": sanitize_text(str(exc), secret)}


def _check_timeout(base, model, secret, headers):
    payload = {"model": model, "messages": [{"role": "user", "content": "说点什么"}], "max_tokens": 50}
    t0 = time.time()
    try:
        httpx.post(f"{base}/chat/completions", json=payload, headers=headers, timeout=0.001)
        return {"name": "超时行为", "ok": False, "detail": "极短超时未触发"}
    except httpx.TimeoutException:
        return {"name": "超时行为", "ok": True, "detail": f"正确抛出超时（{time.time()-t0:.3f}s）"}
    except Exception as exc:  # noqa: BLE001
        return {"name": "超时行为", "ok": True, "detail": f"触发 {type(exc).__name__}（{time.time()-t0:.3f}s）"}


def _check_error(base, secret, headers):
    payload = {"model": "not-a-real-model-xyz", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5}
    try:
        resp = httpx.post(f"{base}/chat/completions", json=payload, headers=headers, timeout=30)
        return {"name": "错误处理", "ok": True, "detail": sanitize_text(f"HTTP {resp.status_code}: {resp.text[:160]}", secret)}
    except Exception as exc:  # noqa: BLE001
        return {"name": "错误处理", "ok": True, "detail": sanitize_text(f"{type(exc).__name__}: {exc}", secret)}


@router.post("/verify-model")
def verify_model():
    settings = get_settings()
    if not settings.is_model_configured:
        return {"configured": False, "model": settings.deepseek_model_id, "results": []}

    base = settings.deepseek_api_base_url.rstrip("/")
    model = settings.deepseek_model_id
    secret = settings.deepseek_api_key
    headers = {"Authorization": f"Bearer {secret}", "Content-Type": "application/json"}

    results = [
        _check_model_id(base, model, secret, headers),
        _check_json(base, model, secret, headers),
        _check_timeout(base, model, secret, headers),
        _check_error(base, secret, headers),
    ]
    return {"configured": True, "model": model, "base": base, "results": results}
