# 02 · 知识生命周期与数据结构报告

## Migration 策略

`0018` 不重复创建阶段1已有的四类知识结构：

- `product_knowledge_versions`
- `service_knowledge_versions`
- `knowledge_documents`
- `embedding_records`

本次对这些表做增量加固，并新增 `knowledge_chunks`。Migration 会识别本地 `create_all` 可能预建的空 Chunk 表，保留既有行并只补 tenant 外键和索引，不重复造表。

## 当前数据结构

产品/服务知识版本记录：

- tenant、entity、单调递增 version；
- `draft / published / superseded / withdrawn` 状态；
- source type/name、checksum、owner confirmed time、published/withdrawn time；
- supersedes 关系与 embedding status。

KnowledgeDocument 记录：

- tenant、entity type/id、knowledge version；
- confirmed、active、status、source、checksum；
- 只保留已确认发布的权威知识文档，旧版不会删除。

KnowledgeChunk 记录：

- tenant、document、chunk index、text、metadata、status、checksum；
- MVP 每份短知识卡使用一个 Chunk，接口保留后续确定性切分扩展点。

EmbeddingRecord 记录：

- tenant、document/chunk、knowledge version；
- provider、model、dimension、checksum、status、error code；
- `vector_ref` 只保存本地紧凑 JSON 向量，不依赖外部向量库。

## 生命周期

1. 管理员提交资料后只生成 Proposal。
2. 统一确认再次读取权威实体和当前知识版本。
3. 确认事务创建新版本、Document、Chunk；旧版本改为 superseded 但不删除。
4. 本地索引成功时记录 provider/model/dimension/checksum；失败时知识仍保持 published，索引标记 `index_failed`，检索降级到实体精确或关键词。
5. 撤回也先生成 Proposal；确认后版本、文档、Chunk 和索引退出 active，历史证据仍可审计。

## 审计

发布、撤回和重建索引均写入 `release_audits`，记录 tenant、actor、release/version、动作和前后状态。模型常识不能成为 source，解析器或 AI 不能直接创建权威知识行。
