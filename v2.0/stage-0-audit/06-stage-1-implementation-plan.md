# 06 · 阶段1 实施计划

版本：v2.0-rc1 阶段0
日期：2026-08-21

> 本文件仅为计划预告，阶段0 未执行任何阶段1 内容。

## 阶段1 目标（按 07-development-roadmap-vscode-handoff.md）

数据基础与权限：建表、RBAC、迁移、回滚、种子数据、V1 账本回归。

## 实施步骤

1. 引入 Alembic，initial baseline 锁定 V1 当前 schema（7 张表）。
2. 新增 Tenant / User / Invite 表；现有业务表加 tenant_id 并回填默认租户。
3. 新增 CustomerFact、Product/ProductAlias、KnowledgeVersion、Conversation、Recommendation、Release 等表。
4. owner/admin RBAC 骨架（后端强制，非仅前端隐藏）。
5. 导入 `data/` 目录合成种子数据（商品/服务 → 客户 → 知识文档）。
6. `ledger_entries.product_name` 迁移为 UnclassifiedProduct 草稿映射。
7. V1 账本回归测试全绿（现有 100 个测试保持通过）。
8. `/verify/v2-stage-1` 验证页。

## 阶段1 验收停点（预告）

- 新表可建、Migration 可回滚；
- owner/admin 权限隔离正确；
- V1 账本回归通过；
- 种子数据可导入；
- 不修改/删除 V1 权威字段与历史数据。

## 后续阶段概览（预告）

阶段2 双端应用壳与闭环 → 阶段3 多日会话与统一 Proposal → 阶段4 客户事实与产品实体 → 阶段5 RAG 知识链路 → 阶段6 推荐/话术/反馈 → 阶段7 AI 测评与发布 → 阶段8 完整联调。
