# 02 · Schema 与表报告

版本：v2.0-rc1 阶段1
日期：2026-08-21

## 总表数：38（V1 7 张 + alembic_version + V2 新表 30 张）

## V1 表（保留，新增 tenant_id 列）

customers、customer_aliases、services、packages、ledger_entries、prompt_versions、agent_proposals。
V1 权威字段（如 packages.opening_used_count）未删除、未重命名。

## V2 新表（30 张）

| 分类 | 表 |
|---|---|
| 租户/身份 | tenants、users、invites |
| 客户事实 | customer_facts |
| 产品 | products、product_aliases |
| 知识/Embedding | product_knowledge_versions、service_knowledge_versions、knowledge_documents、embedding_records |
| 会话/语音 | conversation_threads、conversation_sessions、messages、message_blocks、entity_mentions、pending_actions、context_summaries、voice_turns |
| 推荐 | recommendation_rules、recommendations、message_drafts、follow_up_feedback |
| 发布治理 | ai_config_drafts、prompt_releases、rag_releases、recommendation_releases、evaluation_runs、evaluation_case_results、release_audits、owner_ai_feedback |

## 关键约束

- CustomerFact：fact_type、display_value、evidence_text、confidence、confirmation_status、sensitivity_level、valid_from/valid_to、supersedes_id（版本化，不覆盖）。
- Product：canonical_name、brand、category、specification、lifecycle_status、knowledge_status、version。
- ProductAlias：alias、normalized_alias、source。
- 所有写表含 created_at；业务表含 updated_at/deleted_at（软删除）。
- EmbeddingRecord 只建结构，未接任何 Embedding 供应商。
- Conversation / Recommendation 只建表与状态枚举，未实现业务流程。
