# 10 · DeepSeek V4 离线协议整改

## 1. 验证状态

此前唯一授权窗口已执行累计 1 次隔离真实请求：模型 `deepseek-v4-pro`、官方端点 `https://api.deepseek.com`、HTTP 200、`external_call_count=1`。返回候选未通过本地严格校验，运行状态为 `rejected_fallback`。

安全门禁按设计生效：CustomerFact、Product、LedgerEntry 均 0 写入，只保留 1 个未确认 Proposal；Key 和模型 raw 输出未暴露。该结果不构成真实模型验收。

本轮只完成离线协议整改，没有发起第二次真实请求。下一次真实验证必须重新获得明确授权。

## 2. 官方协议对齐

根据 DeepSeek 官方 [JSON Output](https://api-docs.deepseek.com/guides/json_mode/) 与 [Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode) 文档，`DeepSeekAdapter.chat` 的非流式结构化请求现在明确包含：

- `response_format={"type":"json_object"}`；
- `thinking={"type":"disabled"}`；
- `temperature=0.0`；
- `stream=false`；
- `max_tokens=2000`。

两个 `chat` 调用方的 system prompt 都要求只输出 JSON。阶段4候选 prompt 新增完整合法示例，覆盖全部顶层字段、facts 与 product_purchase 嵌套字段及 `null` 用法，同时继续禁止实体 ID、推断和非原文证据。

`check_connectivity` 的最小 ping payload 未修改。

## 3. 离线测试证据

- `backend/tests/test_deepseek_adapter_contract.py`：2 项 MockTransport 契约测试；
- 断言模型 ID、messages、JSON Output、thinking disabled、temperature、max_tokens 和 stream；
- 成功响应与包含测试密钥的 HTTP 错误均不泄露 Key；
- 阶段4完整示例可被 `parse_and_validate` 严格接受；
- 全量后端：224 passed；
- 前端：38 passed（7 个测试文件）；
- 生产构建：75 modules transformed。

## 4. 当前停点

`ENABLE_V2_REAL_MODEL=false`，真实模型路径未启用。本轮完成后继续停在阶段4，不开始阶段5、RAG、Embedding 或推荐。
