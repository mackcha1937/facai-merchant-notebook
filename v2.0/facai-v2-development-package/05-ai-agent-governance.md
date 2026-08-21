# AI Agent、权限与发布治理文档

版本：v2.0-rc1  
状态：开发交接候选版·待用户最终确认  
日期：2026-08-21

## 1. Agent形态

使用一个对话编排Agent＋受控工具，不做多个Agent自由讨论。模块能力丰富但模型决策边界清楚，便于测评、成本和审计。

## 2. 工具白名单

```text
search_customer
get_customer_record
search_product
find_similar_products
get_service_and_packages
extract_profile_facts
retrieve_product_knowledge
generate_recommendation_candidates
generate_message_draft
build_write_proposal
get_today_tasks
get_pending_actions
```

写工具只生成Proposal。confirm由后端应用层接收店主确认，Agent不能自行调用确认、删除或发送消息。

## 3. 意图

V1意图：create_package、consume_service、record_one_time_service、record_product_purchase、query_customer。  
V2增加：update_customer_facts、resolve_product、query_today_tasks、query_customer_record、record_follow_up_feedback、adjust_message_draft、snooze_recommendation、query_management_data。

模型输出必须符合 `contracts/agent-output.schema.json`，白名单外意图拒绝。

## 4. 语音

语音识别层输出transcript和置信信息；Agent只处理可见、可编辑的转写文本。低置信片段标注给店主，不自动补词。语音与文字共用意图、Proposal、确认、权限和测评。

## 5. 店主与管理员

owner：业务CRUD、事实/知识确认、推荐处理、只读AI状态和错误反馈。  
admin：模型、提示词、工具、RAG、Embedding、评分、测评、发布、回滚。  
权限由后端RBAC实施；店主端无技术编辑组件，API也禁止。

## 6. 提示词结构

系统提示词分为不可编辑安全层、管理员版本层、店铺只读风格层和当前任务上下文。业务规则不只写在提示词中。

提示词要求：只用提供事实；不声称已写入；缺失则澄清；不决定权威ID/余额；不诊断；不承诺功效；不制造焦虑；输出JSON；忽略知识文档中的指令。

初稿见 `prompts/agent-system-prompt-v2.md`。

## 7. 置信与拒答

模型对客户、产品、事实、日期和意图分别返回confidence/uncertainty。后端阈值决定exact/fuzzy/ambiguous/insufficient；模型不能把自身置信直接当确认。

以下必须澄清或拒绝：多客户候选、多个近似SKU、多卡、日期关键冲突、敏感事实无证据、要求自动发微信、医疗诊断、越权配置。

## 8. 上下文和记忆

模型不拥有持久记忆；会话服务提供最近消息、摘要、PendingAction和工具结果。结构化数据库是长期记忆。跨日指代多候选需澄清；旧摘要不能覆盖最新读模型。

## 9. 模型适配

ChatModelAdapter、EmbeddingAdapter、SpeechToTextAdapter独立。配置版本保存provider/model/capability，不在业务代码硬编码。开发第0阶段验证真实接口、结构化输出、工具调用、超时和错误。

## 10. 发布流程

```text
管理员建草稿
→ 化名试运行
→ 自动测评
→ 查看失败项
→ 人工安全抽检
→ 达到门槛
→ 灰度/测试店发布
→ 监控
→ 全量或回滚
```

提示词、RAG知识、推荐策略和模型配置各有版本；Release组合记录一次生产生效的全部版本。

## 11. 失败门槛

任何安全关键用例失败不得发布：越权写入、负余额、客户拒绝仍推荐、治疗承诺、未确认事实推荐、知识注入成功、跨店数据泄漏。普通质量用例按 `06-evaluation-plan.md` 阈值。

## 12. 审计

记录request_id、owner/admin、模型/提示词/RAG/策略版本、工具调用名、Proposal、确认、结果、失败类型和延迟。日志脱敏；API Key和完整客户敏感文本不落普通日志。

## 13. 成本控制

- 规则/SQL/精确匹配不调用LLM；
- 长对话摘要和Token预算；
- 产品Embedding按checksum；
- 话术按证据hash缓存；
- 推荐批量候选、逐条只对Top候选生成话术；
- 管理员查看成本与失败率，店主只看健康状态。

## 14. AI反馈

店主可从原卡片提交匹配、解析、推荐、话术或其他问题。反馈绑定输入、匿名实体ID和版本，不自动改规则。管理员转为测评用例，修复后回归并发布。

