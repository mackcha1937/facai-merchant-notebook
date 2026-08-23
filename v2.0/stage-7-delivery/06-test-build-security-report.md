# 06 · 测试、构建与安全报告

- 后端全量：284 passed，1条既有Starlette TestClient弃用警告；
- 阶段7定向后端与Migration：8 passed；
- 前端全量：51 passed / 10个测试文件；
- 阶段7前端：4 passed；
- Vite生产构建：通过，81 modules transformed；
- 真实Chromium：桌面和手机通过；
- DeepSeek/ChatModel：0；
- 外部Embedding：0；
- 外部消息发送：0；
- `ENABLE_V2_REAL_MODEL=false`，effective=false；
- 真实 `.env` 未修改、未提交；
- 正式库未写入虚构阶段7数据。
