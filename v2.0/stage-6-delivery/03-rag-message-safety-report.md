# 03 · RAG证据、话术与安全报告

## RAG证据边界

- 推荐只调用阶段5本地 `rag_service.retrieve`；不直接调用外部向量服务。
- 指定 entity type/id，阶段5继续强制 tenant、confirmed、active、published、current version 和实体状态过滤。
- 推荐保存稳定 document/version/source/score/snippet 与结构化 SQL 证据快照；知识更新不会改写旧推荐。
- 当前知识缺失、未确认、旧版、撤回、跨店或实体停用时硬排除。
- 已有当前知识但 RAG/索引运行失败时，仅保留 SQL 交易、余量、日期和规则证据，标记 `degraded`；不得伪造 catalog evidence。
- 没有结构化证据时不生成推荐，相似产品知识不能替代指定产品。

## 本地安全话术

三类候选各有固定安全模板，均以询问感受和需求为主，不假设用完、不制造焦虑、不诊断、不承诺治疗、治愈或保证有效。有限改写仅支持：

- `shorter`：短一点；
- `no_purchase`：不提购买。

模板只读取已保存的客户称呼、实体名称、结构化余量和推荐类型，不把 RAG snippet 或反馈原文拼入话术。客户称呼/实体名称在使用前经过长度、PII、脚本、秘密和提示注入门禁；异常标签使用中性占位。生成后再次执行禁止表达、秘密和长度检查。

## 外发边界

- `MessageDraft` 只用于复制；复制仅记录本地 `copied_at` 审计，不改变推荐为“已联系”。
- 没有微信、短信或其他发送路由、按钮、SDK、Webhook 或后台任务。
- 阶段6不引用 ChatModelAdapter/DeepSeekAdapter；真实模型、外部 Embedding 和外部发送均为 0。
