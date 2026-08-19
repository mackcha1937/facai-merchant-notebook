"""模型输出解析与结构校验测试。"""
import pytest

from app.agent.schema import AgentParseError, parse_model_output


def test_parse_plain_json():
    out = parse_model_output(
        '{"customer_query":"小蓝","customer_match":{"status":"exact"},'
        '"actions":[{"type":"consume_service","service_name":"面部清洁"}],'
        '"needs_clarification":false}'
    )
    assert out.customer_query == "小蓝"
    assert out.actions[0].type == "consume_service"


def test_parse_code_block():
    raw = '好的，结果如下：\n```json\n{"customer_query":"小蓝","actions":[]}\n```'
    out = parse_model_output(raw)
    assert out.customer_query == "小蓝"


def test_invalid_json_raises():
    with pytest.raises(AgentParseError):
        parse_model_output("这不是 JSON")


def test_missing_fields_get_defaults():
    out = parse_model_output('{"customer_query":"x"}')
    assert out.actions == []
    assert out.customer_match.status == "not_found"
    assert out.needs_clarification is False


def test_unknown_fields_ignored():
    out = parse_model_output('{"customer_query":"x","hacky_field":123}')
    assert out.customer_query == "x"
