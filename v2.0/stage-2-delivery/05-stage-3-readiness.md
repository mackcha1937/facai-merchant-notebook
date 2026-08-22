# 05 · 阶段3准备度报告

版本：v2.0-rc1 阶段2归档
归档日期：2026-08-23
当前停点：阶段2完成并暂停，本文不构成阶段3开发授权

## 1. 阶段3目标

按V2路线图，阶段3负责多日会话与统一Proposal：

- 一个持续主Thread和按日Session；
- Message、MessageBlock、ContextSummary和PendingAction持久化；
- 相对日期在首次解析时固定为绝对日期；
- 一次统一确认、单事务、幂等和过期控制；
- 手机/Web跨设备一致性与冲突处理；
- 历史浏览卡重新展开时读取最新权威数据；
- `/verify/v2-stage-3` 验证页和阶段停点。

## 2. 可复用的数据表

阶段1Migration已创建以下结构，阶段3可在审查约束后复用：

- `conversation_threads`
- `conversation_sessions`
- `messages`
- `message_blocks`
- `entity_mentions`
- `pending_actions`
- `context_summaries`
- `voice_turns`
- V1 `agent_proposals`
- V1 `customers`、`services`、`packages`、`ledger_entries`

这些表已经具有tenant_id基础边界，主要父子表已有部分外键，MessageBlock含 `data_version` 字段。
但“表存在”不等于阶段3会话、事务和并发能力已经实现。

## 3. 可复用的现有代码

### 后端

- tenant ContextVar、owner/admin RBAC和仓储tenant过滤；
- V1 Agent解释、Proposal读取、取消、预检查和确认接口；
- V1确认服务的多项统一校验、单事务写入和余额保护；
- V1客户、套餐、账本读写和权威余额计算；
- 阶段2 SpeechToText Adapter接口和Mock实现；
- 阶段1会话相关SQLAlchemy模型和Alembic链。

### 前端

- V2 AppShell手机/Web响应式布局；
- ChatView和ChatComposer；
- 固定卡片组件；
- ContextStack纯逻辑；
- 今日事项纯逻辑；
- Mock语音状态机；
- `/app/chat`、`/app/customers`、`/app/manage` 路由基础。

## 4. 阶段3尚需实现

### 多日会话

- 每个tenant/owner的主Thread创建与唯一性规则；
- 按Asia/Shanghai日期或空闲规则创建Session；
- Message、MessageBlock、EntityMention仓储和API；
- 最近消息、结构化事实和摘要的上下文组装；
- ContextSummary生成、版本和失效规则；
- 历史分页和日期分隔；
- 第二天展示未完成事项，但不自动写入。

### PendingAction与绝对日期

- PendingAction仓储、tenant过滤、状态机和过期任务；
- PendingAction与Thread、Proposal的完整关联约束；
- “昨天、月底、三天后”等相对日期解析为Asia/Shanghai绝对日期；
- 解析时保存绝对日期，跨日继续时不得漂移；
- 过期Proposal重新读取当前数据并重新生成确认。

### 统一Proposal

- V2 Proposal Schema与UI Block Schema映射；
- owner编辑后的后端重新校验；
- request_id/idempotency_key唯一约束；
- expires_at、resolved_absolute_dates、数据版本和stale状态；
- 多项剩余操作单事务，任一失败整组回滚；
- 重复确认返回原结果，不重复写入；
- 并发确认使用数据库约束或条件更新保证只有一次成功；
- 余额、客户、产品或版本变化时返回差异并重新确认；
- 手机/Web同时操作时的冲突回执。

### 前端连接

- 用真实会话/消息/Proposal API替换阶段2Mock fixture；
- 接入SSE `text_delta` 与最终validated block；
- 历史卡重新展开时按data_version读取最新权威数据；
- 确认、取消、失败、重试和过期留在原卡片；
- 写入成功后刷新客户、套餐、账本和相关Block；
- 修复浏览器history与ContextStack不一致；
- 增加焦点、收起、关闭和刷新恢复。

## 5. 阶段3开始前风险

1. `agent_proposals` 当前没有request_id/idempotency_key、过期时间、绝对日期快照或数据版本字段；
2. 现有V1“仅允许pending确认”的逻辑不等于并发条件下的强幂等；
3. `pending_actions` 需要复核Thread/Proposal外键、索引和唯一约束；
4. Thread与Session缺少明确的一店主单主线程和每日Session唯一约束；
5. 阶段2AppShell没有统一使用现有 `useContextStack` Hook，浏览器返回不可靠；
6. UI Block组件与机器可读Schema尚未形成完整映射；
7. 当前今日事项、对话和客户档案仍为Mock，接真实后端时必须防止前端计算覆盖权威数据；
8. 任何新增字段或约束都必须通过新Migration增量实现，不得重置或覆盖V1数据。

## 6. 阶段3验收清单

- [ ] 同一owner重复打开只得到同一个主Thread；
- [ ] 同一天消息进入同一Session，跨日出现日期分隔；
- [ ] 相对日期解析后保存绝对日期和Asia/Shanghai时区；
- [ ] 跨日继续PendingAction时日期不漂移；
- [ ] 过期PendingAction不能提交，可基于当前数据重新生成；
- [ ] 一次输入只出现一次最终写入确认；
- [ ] 多项操作在单事务中全部成功或全部回滚；
- [ ] 重复请求、重复点击和网络重试不重复入账；
- [ ] 手机/Web并发确认时仅一个成功，另一端得到可恢复冲突；
- [ ] 历史浏览卡重新展开显示最新权威数据；
- [ ] 浏览器返回、页面按钮返回、关闭和收起遵循同一ContextStack；
- [ ] 草稿、列表状态和未确认卡在规定范围内恢复；
- [ ] owner不能越权访问其他tenant的Thread、Session、Message或Proposal；
- [ ] 模型或网络失败不产生权威写入，原输入可重试；
- [ ] V1余额、软删除、恢复和全量回归测试继续通过；
- [ ] 阶段3Migration可升级、降级且不破坏V1账本；
- [ ] `/verify/v2-stage-3` 提供双端验证和明确停点。

## 7. 准备度结论

阶段3已有数据库表骨架、V1账本事务能力、tenant/RBAC基础和V2双端前端壳，
但会话仓储/API、Proposal强幂等与并发约束、真实前后端连接尚未实现。

开始阶段3前必须先确认本报告中的交互缺口和数据约束方案。
在用户明确授权之前，保持阶段2停点，不执行阶段3代码、Migration或数据操作。
