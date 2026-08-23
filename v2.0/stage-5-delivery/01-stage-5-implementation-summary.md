# 01 · 阶段5实现总结

## 交付结论

阶段5“RAG 知识链路”已完成，停点为 `/verify/v2-stage-5`。本阶段只建设产品/服务知识的 Proposal、确认发布、版本、来源、Chunk、本地 Embedding、轻量索引与证据检索，没有进入阶段6推荐、Top3、提醒、营销话术或反馈闭环。

阶段5没有调用真实 DeepSeek，也没有调用、下载或购买任何外部 Embedding 服务。运行时为零网络依赖的 `facai-local / char-ngram-sha256-v1 / 32` 本地确定性向量。

## 已完成范围

- `0018_stage5_knowledge_rag` 复用阶段1已建的知识版本、`KnowledgeDocument` 和 `EmbeddingRecord`，增量补齐状态、来源、checksum、当前版本、撤回和索引失败字段；只新增此前必要但不存在的 `knowledge_chunks`。
- 知识草稿、发布、撤回和重建索引仅管理员可执行；店主端只有状态、当前知识和证据检索三个只读能力。
- 发布与撤回使用统一 Proposal；确认前知识版本、文档、Chunk 和 EmbeddingRecord 均为零写入。
- 确认时重新校验管理员权限、tenant、实体状态、当前版本、checksum、安全门禁和权威快照；支持幂等、stale、跨店隔离和事务回滚。
- 当前已确认且 active 的版本才进入检索；旧版、撤回、未确认、停用/合并/删除实体均被排除，但旧证据仍保留供管理员追溯。
- 检索顺序为：指定实体当前版本精确知识 → 实体标准名/别名与关键词 → 同模型同维度的本地向量；融合去重最多返回 5 条稳定证据。
- 指定实体知识不足时直接返回 `knowledge_insufficient`，不会用相似产品替代。
- 返回字段限定为 document、knowledge version、entity、source、score、match 和 snippet；知识明确标记为不可信数据，不能改变权限或指令。

## 权限边界

- 店主只读：`GET /api/owner/knowledge/status`、`GET /api/owner/knowledge`、`POST /api/owner/knowledge/retrieve`。
- 管理员写入：`/api/admin/knowledge/*` 的草稿 Proposal、撤回 Proposal、确认和重建索引。
- 不存在 `/api/owner/knowledge/proposals`；通用 Proposal 确认服务遇到知识动作时也会再次要求管理员角色，避免路径绕过。

## 当前停点

阶段5代码、测试、Migration、构建和本地浏览器验收完成。等待阶段5人工验收，不自动开始阶段6。
