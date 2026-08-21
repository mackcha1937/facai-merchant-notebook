# 04 · DeepSeek 能力验证

版本：v2.0-rc1 阶段0
日期：2026-08-21

## 验证方式

- 脚本：`backend/scripts/v2_stage0_verify_model.py`
- 接口：`POST /api/v2/stage0/verify-model`
- 目标：`base=https://api.deepseek.com model=deepseek-v4-pro`
- 安全：API Key 只从 `backend/.env` 读取，输出全部脱敏，绝不打印 Key。

## 验证结果（真实调用 API，非假装）

| 验证项 | 结果 | 说明 |
|---|---|---|
| 模型 ID 可用性 | ✅ 通过 | `deepseek-v4-pro` 被官方接口接受 |
| 结构化 JSON 输出 | ✅ 通过 | 能输出合法 JSON（customer_query/intent/items 字段正确） |
| 超时行为 | ✅ 通过 | 极短超时正确抛出 TimeoutException（约 0.016s） |
| 错误处理 | ✅ 通过 | 错误模型 ID 返回 HTTP 400 + 清晰错误信息 |

## 关键结论

官方接口错误信息明确返回：

```text
The supported API model names are deepseek-v4-pro or deepseek-v4-flash, but you passed ...
```

即当前账户真实可用模型为 **deepseek-v4-pro** 和 **deepseek-v4-flash**。用户提供的目标名 `deepseek-v4-pro` 真实有效，无需更换。

## 尚未验证（进入阶段1/5 前需真实环境验证）

1. DeepSeek 结构化输出/流式响应/限流的长期稳定性；
2. 工具调用（tool/function calling）能力；
3. SpeechToText 与 Embedding 的真实供应商（见 05）。
