# 01 · Migration 报告

版本：v2.0-rc1 阶段1
日期：2026-08-21

## Migration 列表（8 个，链式）

| 版本 | 内容 |
|---|---|
| 0001_baseline | V1 现有 7 张表（只锁定结构，downgrade 不删表） |
| 0002_tenant_user_invite | Tenant / User / Invite |
| 0003_tenant_id_backfill | 7 张业务表加 tenant_id + 默认租户回填 |
| 0004_customer_fact_product | CustomerFact / Product / ProductAlias |
| 0005_knowledge | 知识版本 / 文档 / EmbeddingRecord |
| 0006_conversation | 会话/语音 8 表 |
| 0007_recommendation | 推荐 4 表 |
| 0008_release | AI 发布治理 8 表 |
| 0009_tenant_integrity_hardening | tenant_id NOT NULL + 外键 + 索引 + 6 子表 tenant_id 回填 |
| 0010_product_name_migration | 历史 product_name → Product 草稿 + product_id 回填 |

## 执行结果（现有 V1 数据库）

1. `alembic stamp 0001_baseline`（表已存在，仅标记版本，不重建）；
2. `alembic upgrade head` 顺序执行 0002~0008，全部成功；
3. 迁移后数据基线一致（见 04 文档）。

## 安全保证

- baseline downgrade 为 pass（不删除 V1 账本表）；
- 0003 downgrade 只移除 tenant_id 列，不删除账本数据；
- 其余 migration downgrade 只 drop 自己新建的表，不碰 V1 表。
