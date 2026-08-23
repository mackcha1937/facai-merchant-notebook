# 09 · 阶段4模型安全审计整改

## 1. 审计结论

本次整改关闭了独立验收发现的模型安全缺口，未扩大阶段4范围。此后在唯一授权窗口执行了累计 1 次隔离真实 DeepSeek 请求；本轮离线协议整改没有新增真实请求。阶段5、RAG、Embedding 和推荐均未开始。

## 2. 阻断项与修复证据

| 阻断项 | 修复 | 自动验证 |
| --- | --- | --- |
| Key 存在即可能产生付费调用 | 新增 `ENABLE_V2_REAL_MODEL`，默认 false；只有 Key 已配置且开关明确为 true 才构造 `DeepSeekAdapter` | 本机 Key 已配置时状态为 `configured=true`、`enabled=false`、`effective=false`，Adapter 零构造 |
| 事实值未受证据约束 | `display_value` 必须由对应 `evidence_text` 直接支持，否则整体拒绝模型结果并回退 | “甲姐皮肤敏感”不能产生“严重过敏，禁止使用所有护肤品”；无 CustomerFact 权威写入 |
| 产品数量可被模型伪造 | 后端从产品 evidence 确定性解析数量，并要求模型数量一致 | “一瓶”解析为 1、“2瓶”解析为 2；模型伪造 999 被拒绝且不能进入 Proposal |
| 原始 PII 可能外发 | Adapter 调用前检测中国手机号、明确标识的微信号和邮箱；命中返回 `pii_fallback`，脱敏后仅走本地规则/人工路径 | 各类 PII 用例均断言 Adapter 未调用、原文未外发或持久化、零权威写入 |

确认、取消和产品候选选择仍由确定性后端命令处理，相关测试均证明不会调用模型。

后续独立验收发现手机号分隔格式及 VX 标签漏检，已通过最小补丁补齐：手机号允许数字间空格或短横线并整体脱敏；微信号补充大小写不敏感的 VX 标签，但 ASCII 标签必须有独立边界及冒号/空格分隔。连续号码、`+86`、空格、短横线、微信号、WX、VX/vx 和邮箱均覆盖直接函数及完整聊天链测试；无标签英文串保持不命中。

## 3. 配置与信息边界

- 开关只从后端环境变量读取，`.env.example` 使用 `ENABLE_V2_REAL_MODEL=false`；
- 状态 API 只分开暴露 `configured`、`enabled`、`effective`，不返回 Key；
- 前端只展示布尔运行状态，不接收或保存 Key；
- 测试默认清空 Key 并关闭开关，模型场景仅使用 MockModel；
- `.env`、真实 Key、PII 原文和模型 raw 输出均未加入提交或测试快照。

## 4. 最终验证

- 后端：224 passed；
- 前端：38 passed（7 个测试文件）；
- 生产构建：通过，75 modules transformed；
- 阶段4模型运行链：39 项 MockModel/安全测试，另有 2 项 MockTransport Adapter 契约测试；
- Migration 往返：`0016 → 0017 → 0016 → 0017`，正式库停留在 `0017_stage4_entity_hardening` 且 `integrity_check=ok`；
- 真实 DeepSeek 请求累计：1 次，HTTP 200，但候选为 `rejected_fallback`；CustomerFact / Product / LedgerEntry 均 0 写入，仅 1 个未确认 Proposal；不构成真实模型验收。

## 5. 停点

下一次真实模型验证仍需店主重新授权。授权前保持 `ENABLE_V2_REAL_MODEL=false`；本整改完成后暂停，不自动开始阶段5。
