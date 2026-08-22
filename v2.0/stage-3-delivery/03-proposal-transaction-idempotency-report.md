# 03 · Proposal 事务与幂等报告

## 1. 统一确认

一次店主输入解析出多项操作时，只创建一个 AgentProposal、一个 PendingAction 和一张 ConfirmCard。解析阶段不写客户、套餐或账本权威数据。

## 2. 状态机

```text
pending → processing → confirmed
pending → cancelled
pending → expired → regenerated（新 Proposal pending）
pending → stale   → regenerated（新 Proposal pending）
```

confirmed、cancelled、expired、stale 均禁止再次直接执行。processing 只在确认事务内部使用。

## 3. 幂等与并发

- `tenant_id + request_id` 防止同一对话请求重复落消息和 Proposal；
- `tenant_id + idempotency_key` 防止网络重试重复创建 Proposal；
- 确认使用 `status=pending AND data_version=请求版本` 条件更新抢占；
- 相同确认幂等键重复请求返回原 `result_json`；
- 不同设备幂等键确认已处理 Proposal 时返回 HTTP 409、原结果与可恢复标记；
- SQLite 锁竞争转换为明确的 concurrent_confirmation 冲突，不伪造成功。

真实双 Session 并发测试验证：手机/Web 同时确认时恰好一个 `confirmed`，另一端为 `conflict`，账本只新增一条。

## 4. 事务与回滚

确认流程先重检租户、owner、角色、Proposal 状态、有效期、data_version、客户、服务、套餐和余额，再执行全部 action。所有 action、Proposal 结果、PendingAction 和回执在同一 Session 事务中提交。

测试覆盖了两个 action 单项预检都可通过、但合计超过余额的运行时失败：第一项临时写入后第二项失败，整个事务回滚，账本新增数为 0，Proposal 恢复 pending。

## 5. stale 与差异

创建 Proposal 时保存客户、服务、套餐、已用次数和剩余次数的权威快照。确认前重新生成快照并逐对象比较；不一致时：

- Proposal 与 PendingAction 标记 stale；
- 旧卡禁止执行；
- 返回 before/current 差异；
- 聊天中保存冲突 ReceiptCard；
- 只能基于当前数据重新生成并再次确认。
