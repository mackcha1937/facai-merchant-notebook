# 后端开发文档：发财 V2 技术架构

版本：v2.0-rc1  
状态：开发交接候选版·待用户最终确认  
日期：2026-08-21

## 1. 架构目标

在不破坏V1账本的前提下，增加客户事实、产品实体、知识版本、推荐、RAG、多日会话、双端同步和管理员治理。后端是权威边界；AI只解析、检索和表达。

## 2. 分层

```text
api/             路由、认证、SSE、Schema
application/     用例、Proposal编排、事务、权限
domain/          账本、客户事实、产品、推荐强制规则
repositories/    仓储接口
infrastructure/  SQLite/PostgreSQL、模型、Embedding、向量索引、调度
agent/           对话编排、工具注册、输出校验
rag/             知识处理、检索、重排、证据快照
recommendation/  候选、过滤、评分、去重和状态机
conversation/    Thread、Session、摘要、EntityMention、PendingAction
read_models/     客户档案、今日事项、产品状态等聚合读模型
admin/           草稿、测评、发布、回滚、审计
```

## 3. 核心规则

- Agent不得直接仓储写入；
- 所有写操作先生成Proposal，确认时重新校验；
- 多项确认单事务、幂等；
- 账本余额由有效LedgerEntry派生；
- AI事实和知识未经店主确认不得进入正式推荐；
- 店主不能修改AI技术配置，后端RBAC强制；
- 聊天摘要不覆盖结构化数据；
- 推荐先强制过滤再评分，大模型不能恢复被排除项；
- RAG内容永远按数据处理，不作为系统指令；
- 模型失败不阻断人工账本。

## 4. 数据模型

### 4.0 Tenant与身份边界

即使MVP只有一位店主，也从第一天建立 `Tenant`，避免未来邀请码、多店铺或员工账号接入时重构全部数据。

```text
Tenant: id, display_name, status, created_at
User: id, tenant_id, role(owner/admin), status, last_login_at
Invite: id, tenant_id, code_hash, role, expires_at, used_at
```

所有业务表必须含tenant_id或能通过不可绕过的外键链定位tenant；仓储方法默认接收tenant_id，禁止先按对象ID查询再在应用层过滤。管理员跨tenant排障使用单独的受审计权限，不复用店主接口。

### 4.1 继承V1

Customer、CustomerAlias、Service、Package、LedgerEntry、PromptVersion、AgentProposal。V1迁移先备份，使用显式数据库Migration。

### 4.2 CustomerFact

```text
id, customer_id, fact_type, display_value, normalized_value,
evidence_text, source_type, source_id, confidence,
confirmation_status, sensitivity_level,
valid_from, valid_to, supersedes_id,
created_at, updated_at, deleted_at
```

系统计算事实使用source_type=system，不使用LLM置信度。冲突以新记录supersede旧记录，不直接覆盖。

### 4.3 Product与ProductAlias

```text
Product: id, canonical_name, brand, category, specification,
        lifecycle_status, knowledge_status, owner_id, version, deleted_at
ProductAlias: id, product_id, alias, normalized_alias, source, deleted_at
```

生命周期：draft、active、inactive、replaced、deleted。知识状态：incomplete、pending_confirmation、confirmed、index_failed、indexed。

### 4.4 ProductKnowledgeVersion / ServiceKnowledgeVersion

```text
id, entity_id, version, content_json, source_refs,
owner_confirmed_at, published_at, embedding_status,
created_by, created_at
```

### 4.5 KnowledgeDocument / EmbeddingRecord

```text
KnowledgeDocument: id, entity_type, entity_id, knowledge_version,
                   text, metadata_json, status, checksum
EmbeddingRecord: document_id, embedding_provider, embedding_model,
                 dimension, vector_ref, checksum, indexed_at
```

### 4.6 RecommendationRule / Recommendation

```text
RecommendationRule: id, rule_type, version, conditions_json,
                    hard_exclusions_json, score_config_json, status
Recommendation: id, customer_id, subject_type, subject_id,
                trigger_type, rule_version, score,
                evidence_snapshot, knowledge_versions,
                status, unread_at/read_at/handled_at,
                snoozed_until, generated_at, expires_at
```

状态：new、viewed、copied、contacted、snoozed、converted、not_needed、not_suitable、dismissed、cancelled、expired。

### 4.7 MessageDraft / FollowUpFeedback

保存生成话术版本、店主最终复制文本、反馈原文、提取事实Proposal、确认结果和下次提醒。

### 4.8 会话模型

```text
ConversationThread: id, owner_id, created_at, last_active_at
ConversationSession: id, thread_id, session_date, summary, started_at, ended_at
Message: id, session_id, role, content, message_type, created_at
MessageBlock: id, message_id, block_type, payload_json, state, data_version
EntityMention: message_id, entity_type, entity_id, surface_text
PendingAction: id, thread_id, proposal_id, status, expires_at
ContextSummary: session_id, topics, entity_ids, pending_ids, generated_at
```

### 4.9 VoiceTurn

```text
VoiceTurn: id, tenant_id, owner_id, thread_id,
           audio_object_ref, transcript, transcript_segments,
           stt_provider, stt_model, confidence,
           status, expires_at, created_at
```

- 浏览器使用MediaRecorder采集，先上传临时对象，再调用SpeechToTextAdapter；
- 转写文本必须返回前端并允许修改，修改后的文本才进入 `/chat/turn`；
- 低置信片段按时间段标记，不由大模型静默补词；
- 音频默认只为转写和失败重试短期保存，开发默认24小时自动删除；正式保存期限由隐私设置明确配置；
- 音频、转写、文字输入共用同一意图、Proposal、权限、确认、审计和幂等流程；
- “语音操作”不是新增一套写接口，避免点击和语音出现不同业务规则。

### 4.10 阅读状态

Recommendation或TaskReceipt保存owner_id、read_at、handled_at和updated_at。内容更新且updated_at>read_at时重新未读。未处理数和未读数分别聚合。

### 4.11 AI配置与发布

```text
AIConfigDraft, PromptRelease, RagRelease, RecommendationRelease,
EvaluationRun, EvaluationCaseResult, ReleaseAudit, OwnerAIFeedback
```

店主只读状态来自脱敏聚合表，不返回配置正文或密钥。

## 5. Proposal与事务

流程：interpret→resolve entities→precheck→proposal→owner edits→confirm→recheck→transaction→receipt。

- Proposal记录original_input、resolved_absolute_dates、prompt/model版本、候选和修改；
- 确认仅允许pending状态；
- request_id/idempotency_key唯一；
- 新产品＋购买＋客户事实可单事务；
- 任何一项失败整组回滚；
- 重复确认返回原结果，不重复写入；
- 余额/版本冲突使Proposal stale，返回新状态重新确认。

## 6. 产品解析管线

```text
normalize
→ exact canonical/alias
→ fuzzy string retrieval
→ embedding retrieval
→ optional LLM adjudication
→ backend thresholds/status
→ owner confirmation
```

LLM不能生成权威产品ID。候选必须来自后端。确认新产品时名称规范化、品牌/规格冲突和重复键再次检查。

## 7. 推荐管线

1. SQL规则生成候选：复购周期、服务周期、套餐余量；
2. 强制过滤：不接受营销、不适/禁忌、产品停用、知识未确认、冷却、近期已联系；
3. 可审计评分；
4. RAG检索产品/服务知识；
5. 证据完整性检查；
6. LLM生成推荐解释和话术；
7. 安全后处理；
8. 去重并持久化Recommendation；
9. 主动展示每天Top3，其余可查询；
10. 店主反馈更新状态，但不在线训练模型。

## 8. 多日上下文组装

每次模型调用按Token预算组装：系统提示词→当前输入→当前PendingAction→最近相关消息→当日摘要→工具查询的最新对象→少量RAG证据。

- 不发送全历史；
- Thread永久，Session按本地日期或4小时空闲分段；
- Session摘要只保存主题、实体ID和未完成项；
- “她/刚才/第二个”仅在活跃上下文解析；跨日多候选必须澄清；
- 相对时间立即解析成绝对时间和Asia/Shanghai；
- 历史卡片携带data_version，重新展开拉取最新读模型。

## 9. API建议

### 9.1 店主端

```text
POST /api/owner/chat/turn
POST /api/owner/voice/transcriptions
GET  /api/owner/voice/transcriptions/{id}
DELETE /api/owner/voice/transcriptions/{id}
GET  /api/owner/chat/history
GET  /api/owner/chat/pending
POST /api/owner/proposals/{id}/confirm|cancel|edit
GET  /api/owner/today-tasks
POST /api/owner/tasks/{id}/read|snooze|handle
GET  /api/owner/customers
GET  /api/owner/customers/{id}/record
GET  /api/owner/customers/{id}/history
GET  /api/owner/products
GET  /api/owner/products/{id}
POST /api/owner/products/{id}/knowledge-proposal
GET  /api/owner/ai-status
POST /api/owner/ai-feedback
```

已有V1 CRUD继续保留并统一owner范围。

语音转写接口只返回可编辑文本、分段置信度和临时音频过期时间，不执行任何业务写入。前端确认转写文本后，再按普通文字调用 `/chat/turn`。

### 9.2 管理员端

```text
GET/POST /api/admin/ai-config/drafts
GET/POST /api/admin/prompts
POST     /api/admin/evaluations/runs
GET      /api/admin/evaluations/{id}
POST     /api/admin/releases/publish
POST     /api/admin/releases/{id}/rollback
GET      /api/admin/rag/status
POST     /api/admin/rag/reindex
GET      /api/admin/owner-feedback
GET      /api/admin/audit
```

所有接口服务端RBAC；API Key只从密钥配置读取，从不响应前端。

## 10. UI Block协议

`POST /chat/turn`以SSE发送text_delta，最终发送validated_block。Block符合 `contracts/ui-block.schema.json`。模型只能建议block_type和业务字段；后端重建/净化payload。

## 11. 调度

本地：应用启动后按owner+date幂等检查，支持手动刷新。  
远程：服务端定时任务、分布式锁、失败重试、任务运行记录。  
只重算受影响客户；规则/知识发布产生受影响实体清单。

## 12. 缓存与性能

- 读模型缓存客户摘要、今日事项和产品状态；
- 写后精准失效；
- Embedding按checksum去重；
- 相同知识版本不重复向量化；
- 模型上下文与话术按证据hash短期缓存；
- 客户历史游标分页；
- 列表聚合使用数据库索引而非N+1查询。

## 13. 安全与隐私

- 远程前完成认证、HTTPS、tenant_id强制隔离和加密备份；
- 数据库、对象存储、缓存、向量索引和任务队列全部携带tenant边界；
- 客户ID、手机号和微信标识建立最少必要访问控制，列表默认掩码显示手机号；
- 生产数据库密钥、模型Key和对象存储凭证使用服务端密钥管理，前端包、SSE、错误响应和日志均不得出现；
- PII/健康相关事实最少发送并使用化名；
- 模型请求和日志脱敏；
- 客户事实不整体Embedding；
- 知识文件解析隔离，移除脚本/指令性文本并标记来源；
- 文件类型、大小、病毒和内容校验；
- RBAC、审计、密钥轮换；
- 关键写操作、导出、恢复、AI发布记录操作人、tenant、对象、变更前后摘要、request_id和时间；
- 明确定义聊天、转写音频、审计、备份和软删除数据的保留期限；生产清理任务必须可审计；
- 备份至少验证一次可恢复性；恢复到临时库核验后再切换，不能拿生产库直接试恢复；
- 不接受营销为强制过滤；
- 删除聊天不删除已确认账本。

## 14. 降级

- Chat模型失败：保留输入，允许人工表单/模板；
- Embedding失败：exact/fuzzy继续，新产品可草稿入库，禁止语义匹配与跨客户推荐；
- RAG失败：规则提醒＋模板话术；
- 调度失败：顶部显示状态，允许手动检查；
- 网络失败：不执行权威写入，原地重试；
- 数据库冲突：返回当前版本和差异，重新确认。

## 15. 数据迁移

1. 备份V1数据库；
2. 添加新表，不重命名/删除V1权威字段；
3. 将V1自由文本product_name迁移为UnclassifiedProduct映射草稿；
4. 建立CustomerFact空集合，不从历史聊天自动推断；
5. 生成读模型；
6. 使用化名数据验证；
7. 回滚脚本只回滚Schema/新功能，不破坏V1账本。

## 16. 测试

- 领域单元、仓储、API、事务、幂等、RBAC；
- 产品匹配、推荐过滤、RAG证据和话术安全；
- 多日日期、PendingAction、阅读状态和跨设备冲突；
- AI不可用降级；
- Migration备份与回滚；
- `eval/ai-evaluation-cases.jsonl`自动回归。
