# 03 · 数据库与迁移风险

版本：v2.0-rc1 阶段0
日期：2026-08-21

## 1. 风险点

1. **无迁移工具**：V1 用 `create_all`，无 Alembic；V2 必须引入显式 Migration，否则无法安全加表/加字段。
2. **无 tenant_id**：V2 从第一天要求 Tenant 边界，需给现有表加 tenant_id 并回填默认租户。
3. **product_name 自由文本**：V1 的 `ledger_entries.product_name` 是自由文本，V2 要迁移为 Product 实体（UnclassifiedProduct 草稿映射），不能直接重命名/删除字段。
4. **不能覆盖 V1 权威字段**：`packages.opening_used_count`、`ledger_entries` 等是权威余额来源，迁移只增不删不重命名。

## 2. 迁移策略（按 03-backend-architecture.md 第15节）

1. 先备份（`./backup.sh`，已执行）；
2. 引入 Alembic，初始 baseline 锁定 V1 当前 schema；
3. 新增表（不重命名/删除 V1 权威字段）；
4. `product_name` 迁移为 UnclassifiedProduct 映射草稿；
5. 建立 CustomerFact 空集合（不从历史聊天自动推断）；
6. 生成读模型，化名数据验证；
7. 回滚脚本只回滚 Schema/新功能，不破坏 V1 账本。

## 3. V2 计划新增的表（来自 03-backend-architecture.md 第4节）

- Tenant / User / Invite
- CustomerFact
- Product / ProductAlias
- ProductKnowledgeVersion / ServiceKnowledgeVersion
- KnowledgeDocument / EmbeddingRecord
- RecommendationRule / Recommendation
- MessageDraft / FollowUpFeedback
- ConversationThread / ConversationSession / Message / MessageBlock / EntityMention / PendingAction / ContextSummary
- VoiceTurn
- 阅读状态字段（Recommendation/TaskReceipt 的 read_at/handled_at）
- AIConfigDraft / PromptRelease / RagRelease / RecommendationRelease / EvaluationRun / EvaluationCaseResult / ReleaseAudit / OwnerAIFeedback

## 4. 当前未执行迁移

阶段0 未做任何 Migration，未建任何新表，未改任何 V1 数据。以上仅风险分析与计划。
