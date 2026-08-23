# 08 · 阶段5状态统计租户隔离整改

## 独立审计问题

基线 `7dcf966` 的 `/api/v2-stage5/status` 四项 counts 使用全库统计，可能向当前店铺泄露其他 tenant 的知识规模。该问题只影响阶段5验证状态计数，不代表知识列表或 RAG 检索已经跨店返回内容。

## 修复

- `knowledge_documents`：限定 `KnowledgeDocument.tenant_id == get_current_tenant_id()`。
- `active_documents`：在 tenant 条件外，同时要求 `confirmed=true`、`active=true`、`status=published`、`withdrawn_at IS NULL`。
- `knowledge_chunks`：限定 Chunk tenant，并关联 KnowledgeDocument 后再次限定父文档 tenant。
- `embedding_records`：限定 EmbeddingRecord tenant，并关联 KnowledgeDocument 后再次限定父文档 tenant。

父文档关联过滤用于防御异常错 tenant 子记录：即使 Chunk 或 EmbeddingRecord 自身错误标成当前 tenant，只要所属 KnowledgeDocument 属于其他店铺，就不会进入计数。

## API 级回归

新增跨 tenant 用例：

1. tenant1 发布一份知识，四项计数均为 1。
2. tenant2 发布完整 Document/Chunk/Embedding。
3. 额外插入“tenant_id 标为 tenant1、父文档属于 tenant2”的异常 Chunk 与 EmbeddingRecord。
4. tenant1 再次请求状态 API，四项计数与步骤1完全一致。
5. tenant1 的 owner status、知识列表和指定实体检索仍只返回 tenant1 数据。

## 验证结果

- 定向：3 passed。
- 后端全量：253 passed。
- 前端：42 passed。
- 生产构建：77 modules transformed。
- DeepSeek：新增调用 0。
- 外部 Embedding：0。
- 阶段6：未开始。
