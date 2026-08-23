# 06 · 测试、构建与安全审计报告

## 最终自动测试

- 后端：273 passed；唯一警告为既有 Starlette TestClient/httpx 弃用提示。
- 前端：45 passed / 9 test files。
- 生产构建：Vite 通过，79 modules transformed。

阶段6定向覆盖包括：

- REC-001～005：三类候选、权威余额、剩3次不续费、明确不适硬排除、7天冷却和重复幂等；
- SAF-001～005：无医疗承诺/诊断、秘密与提示注入不进入话术、跨 tenant 隔离；
- E2E-002：RAG异常仅保留结构化证据并标记 degraded，不伪造知识；
- LOOP-004：打开列表不批量已读，逐条 `read_at`，未查看与未处理分离；
- Top3按客户去重、其余可查询；内容checksum不变不重复红点，内容变化才重新未读；
- 未确认事实零采用、停用/撤回/缺失知识和跨店零泄漏；
- 拒绝后零再推，明确解除后恢复；snooze 到期、expired、data version 冲突和动作幂等；
- 证据快照版本追溯；开发包 recommendation JSON Schema 自动校验；
- 安全模板、“短一点”“不提购买”、复制不等于联系、外发能力为0；
- 反馈提取确认前 CustomerFact/账本/提醒零权威写入，确认后事务写入；
- `0019→0018→0019`、create_all预建空表兼容和阶段1～5全回归。

## 安全边界

- 自动测试和浏览器运行均设置 `ENABLE_V2_REAL_MODEL=false`。
- DeepSeek/ChatModel 新增调用0；外部Embedding调用0；模型下载0；外部消息发送0。
- API Key 只存在于后端环境配置边界，没有进入前端、日志、测试快照或交付文档。
- `git diff --check`、跟踪/新增文件真实凭据长度扫描和正式库 integrity/FK 检查均纳入提交前审计。
