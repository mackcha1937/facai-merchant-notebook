# 11 · 阶段4隔离真实模型验收报告

## 1. 验收结论

阶段4真实模型隔离控制用例验收通过。累计真实 DeepSeek 请求 2 次，均 HTTP 200：

- 第 1 次：`model_runtime.status=rejected_fallback`；
- 经 `6d44e42` 完成 JSON Output 与 non-thinking 离线协议整改；
- 第 2 次：`model_runtime.attempted=true`、`status=validated`、`intent=product_purchase`。

两次请求均来自各自独立授权。本次只补充验收记录，没有发起任何新的模型请求。

## 2. 隔离数据与结构化结果

控制输入全部为虚构数据：虚构顾客星澜买了星河面霜一瓶，偏好清爽。

- 后端客户解析：虚构顾客星澜；
- 产品候选：`query=星河面霜`、`quantity=1`、`evidence=买了星河面霜一瓶`、`source=model`；
- 事实候选：`display_value=清爽`、`evidence=偏好清爽`、`source=model`；
- 产品权威匹配：`product_match=not_found`；
- 产品候选数：0，满足最多 3 个的限制；
- 只生成 1 个未确认的 `resolving` Proposal。

报告只记录通过本地严格校验后的结构化字段，不保存或展示模型 raw 输出。

## 3. 零确认与安全边界

没有执行店主确认。确认前数据库检查结果：

- CustomerFact：0 写入；
- Product：0 写入；
- LedgerEntry：0 写入；
- AgentProposal：1 个，状态为 `resolving`。

API Key 未出现在响应、日志、前端或交付记录中；模型 raw 输出未返回。隔离临时数据库已删除，真实 `.env` 未修改。

## 4. 当前运行状态

- `isolated_validation=passed`；
- `total_paid_calls=2`；
- 常驻 `ENABLE_V2_REAL_MODEL=false`；
- `enabled=false`、`effective=false`。

隔离验收通过不等于开启常驻付费调用。任何新增真实请求必须重新获得明确授权。

## 5. 阶段边界

阶段4在此暂停。阶段5、RAG、Embedding 和推荐均未开始，等待后续单独指令。
