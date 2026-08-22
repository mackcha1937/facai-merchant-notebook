# 01 · 阶段3实现总结

版本：v2.0 阶段3

日期：2026-08-23

范围：多日会话与统一 Proposal 闭环

## 1. 完成内容

- 每个 `tenant_id + owner_id` 唯一主 Thread；
- Asia/Shanghai 自然日唯一 Session；
- Message、MessageBlock、EntityMention、ContextSummary、PendingAction 已接通仓储与 API；
- 历史消息支持游标分页、Session 日期分隔和刷新恢复；
- 相对日期首次解析为带时区的绝对日期并写入 Proposal；
- PendingAction 支持 pending、completed、cancelled、expired、stale、regenerated；
- 一次输入只创建一张统一 ConfirmCard；
- Proposal 具备 request_id、idempotency_key、expires_at、resolved_absolute_dates、data_version、权威快照和结果快照；
- 确认采用条件更新抢占、事务写入、幂等回放和跨设备冲突回执；
- JSON API 与 SSE `text_delta` / `validated_block` 均已提供；
- 手机和 Web 共用主 Thread、消息、PendingAction、Proposal、阅读状态和权威读模型；
- 客户档案与服务详情重新展开时读取最新后端派生余额；
- `/verify/v2-stage-3`、`/app/chat`、`/app/customers`、`/app/manage` 已接通。

## 2. 数据边界

Agent/受控解析器只生成 Proposal，不直接写权威业务表。账本写入仅发生在店主确认、后端重新校验和数据库事务中。余额继续由未删除的 `package_consumption` LedgerEntry 派生，前端不保存或覆盖权威余额。

## 3. 未扩大范围

本阶段没有实现客户事实、新产品 AI 识别、RAG、Embedding、推荐算法或真实语音供应商。DeepSeek 配置保持原样；自动测试和浏览器验收没有调用收费模型 API。

## 4. 关键文件

- `backend/alembic/versions/0015_stage3_conversation_proposal.py`
- `backend/alembic/versions/0016_stage3_pending_read_status.py`
- `backend/app/application/conversation_service.py`
- `backend/app/application/stage3_proposal_service.py`
- `backend/app/api/routes/v2_stage3.py`
- `frontend/src/pages/v2/ChatView.jsx`
- `frontend/src/pages/v2/AppShell.jsx`
- `frontend/src/pages/v2/VerifyV2Stage3.jsx`

## 5. 停点

阶段3完成后暂停。不得自动开始阶段4。
