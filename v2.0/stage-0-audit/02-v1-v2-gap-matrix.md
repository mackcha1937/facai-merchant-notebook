# 02 · V1/V2 差异矩阵

版本：v2.0-rc1 阶段0
日期：2026-08-21

| 维度 | V1 现状 | V2 要求 | 差异类型 |
|---|---|---|---|
| 租户与身份 | 无 | Tenant + User(owner/admin) + Invite，所有表带 tenant 边界 | 新增 |
| 客户事实 CustomerFact | 无 | 事实/证据/置信度/敏感级别/版本/有效期 | 新增 |
| 产品实体 Product/ProductAlias | product_name 自由文本 | 品牌+名称+规格，别名/模糊/向量匹配，生命周期+知识状态 | 新增 |
| 知识版本/Embedding | 无 | ProductKnowledgeVersion、KnowledgeDocument、EmbeddingRecord | 新增 |
| 推荐 | 无 | 复购/回访/续卡三类，规则候选+强制过滤+评分+RAG+话术 | 新增 |
| 多日会话 | 无 | Thread/Session/Message/PendingAction/摘要/绝对日期 | 新增 |
| 语音 | 无 | SpeechToTextAdapter，转写先可见可改，共用同一确认流程 | 新增 |
| 今日事项/红点 | 无 | unresolved_count + unread_count + read_at/handled_at | 新增 |
| 角色权限 | 单一店主 | owner(业务) + admin(AI配置)，RBAC 后端强制 | 新增 |
| AI 治理 | 仅提示词版本 | 草稿→测评→发布→回滚，模型/提示词/RAG/推荐策略分别版本化 | 新增 |
| Agent 意图 | 5 种 | 增加 update_customer_facts、resolve_product、query_today_tasks 等 | 扩展 |
| UI Block 协议 | 自定义确认卡 | contracts/ui-block.schema.json 六类 Block | 重构 |
| SSE 流式 | 无 | text_delta 流式 + validated_block | 新增 |
| 降级 | 基础 | 模型/Embedding/RAG/调度分别降级，账本始终可用 | 增强 |

## 结论

V2 是在 V1 账本基础上"增量"扩展。V1 的账本、余额、确认、回收站是保留底座，不重写。

## V2 新增意图（相对 V1 的 5 种）

V1：create_package、consume_service、record_one_time_service、record_product_purchase、query_customer。
V2 增加：update_customer_facts、resolve_product、query_today_tasks、query_customer_record、record_follow_up_feedback、adjust_message_draft、snooze_recommendation、query_management_data。
