"""Agent 固定 JSON 结构（Schema）与模型输出解析、校验。

模型输出的 JSON 必须符合这里的结构，后端用 Pydantic 强制校验。
"""
import json
import re

from pydantic import BaseModel, Field


class AgentParseError(Exception):
    """模型输出无法解析或不符合结构（信息面向店主，中文）。"""


class AgentAction(BaseModel):
    type: str
    service_name: str | None = None
    product_name: str | None = None
    quantity: int | None = 1
    price: float | None = None
    total_count: int | None = None
    purchased_on: str | None = None


class CustomerMatch(BaseModel):
    status: str = "not_found"  # exact / fuzzy / not_found / ambiguous
    candidate_ids: list = Field(default_factory=list)  # 后端会忽略并重新计算候选
    new_customer_name: str | None = None


class AgentOutput(BaseModel):
    customer_query: str = ""
    customer_match: CustomerMatch = Field(default_factory=CustomerMatch)
    actions: list[AgentAction] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str | None = None


SCHEMA_EXAMPLE = {
    "customer_query": "小蓝",
    "customer_match": {"status": "exact", "candidate_ids": [], "new_customer_name": None},
    "actions": [
        {
            "type": "consume_service",
            "service_name": "面部清洁",
            "product_name": None,
            "quantity": 1,
            "price": None,
            "total_count": None,
            "purchased_on": None,
        }
    ],
    "needs_clarification": False,
    "clarification_question": None,
}


def _extract_json(text: str):
    text = (text or "").strip()
    if not text:
        raise AgentParseError("模型没有返回内容")

    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # 尝试提取 ```json ... ``` 代码块
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, TypeError):
            pass

    # 尝试提取第一个 { 到最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except (json.JSONDecodeError, TypeError):
            pass

    raise AgentParseError("模型输出无法解析为 JSON，请重试或调整提示词")


def parse_model_output(raw: str) -> AgentOutput:
    data = _extract_json(raw)
    try:
        return AgentOutput.model_validate(data)
    except Exception as exc:  # noqa: BLE001 - 统一转成中文可读错误
        raise AgentParseError(f"模型输出结构不符合要求：{exc}") from exc
