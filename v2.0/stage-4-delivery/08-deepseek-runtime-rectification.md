# 08 · DeepSeek 运行链整改报告

## 1. 整改结论

阶段4 V2 主对话已从“仅保留可选 Adapter 参数”改为真实运行时路径：后端配置 `DEEPSEEK_API_KEY` 时，每个普通 V2 对话轮次会构造 `DeepSeekAdapter` 并调用 `chat`。安全关键的“确认 / 取消 / 选择候选”命令继续由确定性后端状态机处理，不交给模型。

代码路径已用 MockModel 验证，但本次没有执行真实付费 DeepSeek 请求，因此不宣称真实模型已验收。

## 2. V2 模型调用链

```text
POST /api/owner/chat/turn（或 /stream）
  → conversation_service.chat_turn
  → stage4_model_service.run
  → 后端 Settings 判断 DEEPSEEK_API_KEY 是否已配置
  → DeepSeekAdapter.chat（仅产生无 ID JSON 候选）
  → Stage4ModelCandidate 严格 Schema + 原文证据 + 注入检查
  → 后端 customer/product/service 权威检索和 tenant/owner 过滤
  → 规则候选去重合并
  → 唯一 ProductMatchCard / ConfirmCard
  → 店主确认
  → 后端重新校验 + 数据库事务写入
```

模型用于候选级的用户意图、客户称呼、客户事实、产品名、品牌、规格、数量和澄清问题。模型不获取权威 ID 列表，也不能输出可信 ID。

## 3. 验证和降级

- JSON 必须是单一 object，不宽松截取 Markdown 或解释文字；
- 顶层和嵌套对象均 `extra=forbid` 且严格类型；
- intent、fact_type、sensitivity_level 必须属于后端枚举；
- 所有字段有长度/数量上限，置信度为 0—1；
- 客户、事实和产品 evidence 必须是用户原文连续片段，产品名/品牌/规格必须受该 evidence 支持；
- `customer_id`、`product_id`、额外字段、提示注入内容和不一致澄清标记会导致整个结果被拒绝；
- 超时、网络错误、畸形 JSON 或校验失败时，不使用部分模型结果，安全回退到规则/人工路径。

## 4. MockModel 自动测试

`backend/tests/test_v2_stage4_model_runtime.py` 新增 13 项用例：

- 配置模型时实际构造 `DeepSeekAdapter` 并调用 `chat`；
- 合法事实及产品名/品牌/规格进入 ProductMatchCard/Proposal；
- 合法澄清问题进入 V2 回复；
- 超时后规则降级，零权威写入；
- 畸形 JSON、非法枚举、超长字段、非原文证据、越界置信度、伪造 `customer_id/product_id` 和提示注入整体拒绝；
- 未配置 Key 时不构造 Adapter，规则和手动 Proposal 继续可用。
- 阶段4状态 API 只暴露“已配置/未配置”布尔值，不暴露 Key 或配置字段。

pytest 通过 autouse 隔离门默认清空模型配置，所有模型用例都显式注入 MockModel。

## 5. 待授权的真实验证步骤

1. 获得店主单独授权后，创建隔离的临时 SQLite 数据库和纯虚构客户/产品数据；
2. 使用当前后端环境变量构造 `DeepSeekAdapter`，不输出、传递或记录 API Key；
3. 通过 V2 `POST /api/owner/chat/turn` 发送一条含虚构客户、事实和产品名/品牌/规格的控制输入；
4. 验证 `model_runtime.status=validated`、候选证据来自原文、实体 ID 来自后端检索且候选最多 3 个；
5. 在不点击确认的情况下检查 CustomerFact、Product 和 LedgerEntry 均无新写入；
6. 检查应用日志、API 响应和前端不含 Key 或模型 raw 响应；
7. 记录请求次数、脱敏结果和费用边界，然后停止，不进入阶段5。

## 6. 当前停点

整改代码和 MockModel 自动测试已完成。真实 DeepSeek 请求尚未执行，需要单独授权。阶段5、RAG、Embedding 和推荐均未开始。
