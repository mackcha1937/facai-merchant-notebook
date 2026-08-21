# 04 · DeepSeek 能力验证

版本：v2.0-rc1 阶段0（含技术补验）
日期：2026-08-21

## 验证方式

- 脚本：`backend/scripts/v2_stage0_verify_model.py`
- 接口：`POST /api/v2/stage0/verify-model`（受 `ENABLE_STAGE0_VERIFY` 开关保护）
- 目标：`base=https://api.deepseek.com model=deepseek-v4-pro`
- 安全：API Key 只从 `backend/.env` 读取，输出脱敏，绝不打印 Key、不返回敏感错误正文。

## 严格版验证结果（6 项，真实调用 API）

| 验证项 | 结果 | 说明 |
|---|---|---|
| 模型 ID 可用性 | ✅ 通过 | `deepseek-v4-pro` 被官方接口接受（HTTP 200） |
| 结构化 JSON 输出 | ✅ 通过 | 使用 `response_format=json_object`，通过 JSON Schema 全量校验（非只查两字段） |
| 工具调用 | ✅ 通过 | 返回 `tool_calls`，工具名 `lookup_test_customer` 与参数 `name=小红` 均正确；无副作用、不写库 |
| 流式响应（SSE） | ✅ 通过 | `stream=true`，收到 22 个有效内容增量 + `[DONE]` 结束标记 |
| 超时行为 | ✅ 通过 | 明确捕获 `httpx.TimeoutException`（仅超时算通过，DNS/连接/认证等其他异常算失败） |
| 错误模型处理 | ✅ 通过 | 错误模型返回 HTTP 400 + 明确"模型不存在/不支持"错误（2xx/5xx/网络异常算失败） |

## 重要发现（真实行为，已记录）

1. **官方支持的模型**（来自接口错误信息）：
   `deepseek-v4-pro`、`deepseek-v4-flash`、`deepseek-v4-flash-vision-exp`。用户提供的 `deepseek-v4-pro` 真实有效，无需更换。
2. **`deepseek-v4-pro` 是推理模型**：流式响应会先输出思考过程 `delta.reasoning_content`，再输出最终答案 `delta.content`。思考过程会占用 token，因此验证/调用时 `max_tokens` 需足够（本验证用 800），否则最终答案可能为空。这会影响阶段2+ 的 SSE 流式实现、成本和延迟预算。
3. **偶发网络抖动**：模型请求偶发超时/失败，需在后续实现中做好重试与降级（已在 03 文档第14节降级设计中覆盖）。

## 阶段0 验证接口的安全限制

- 接口 `POST /api/v2/stage0/verify-model` **会产生真实模型费用**，因此：
  - 仅在 `ENABLE_STAGE0_VERIFY=true` 时允许调用（`backend/.env` 显式开启），生产默认关闭；
  - 60 秒冷却，防止重复点击；
  - 不返回 API Key 和敏感错误正文；
  - **该接口不得进入正式生产环境**（仅用于阶段0 开发验证）。

## 尚未验证（进入阶段1/5 前需真实环境验证）

1. DeepSeek 流式响应、工具调用在长时间/大批量下的稳定性与限流；
2. SpeechToText 与 Embedding 的真实供应商（见 05）。
