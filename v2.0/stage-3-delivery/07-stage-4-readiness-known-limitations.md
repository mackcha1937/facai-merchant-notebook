# 07 · 阶段4准备度与已知限制

## 1. 阶段4可复用基础

- 统一 Proposal、状态机、data_version、stale 差异和事务执行器；
- 主 Thread、按日 Session、MessageBlock、EntityMention、ContextSummary；
- 跨日 PendingAction 和绝对日期快照；
- 手机/Web 共享状态与 ContextStack；
- 最新权威客户/服务读模型入口；
- SSE text_delta 与 validated_block 协议入口；
- tenant/owner 查询边界和真实并发冲突回执。

## 2. 已知限制

- 阶段3受控解析器只识别已有客户化名、已有启用服务、次数和日期，用于本阶段闭环验证；不是阶段4的新产品或客户事实 AI 识别；
- ContextSummary 当前为结构化摘要，不调用大模型生成自然语言摘要；
- SSE 在受控解析下发送两个确定事件，不模拟模型 token 逐字输出；
- 本地开发身份仍由服务端本地配置提供，正式登录与远程 HTTPS 属于后续远程阶段；
- SQLite 并发锁竞争会转换为可恢复冲突；远程数据库可继续使用同一条件更新协议；
- 今日事项在阶段3只聚合 PendingAction，推荐事项尚未开发；
- 真实语音供应商、客户事实、产品实体、RAG、Embedding 和推荐均未开始。

## 3. 阶段4门禁建议

阶段4开始前应以本阶段提交为基线，继续使用 Proposal 写入边界，不允许事实或产品识别 Agent 直接写数据库。产品候选和客户事实必须合并进同一最终确认卡，并复用 stale、事务、幂等和跨设备冲突协议。

## 4. 当前停点

阶段3已完成并暂停，等待人工验收。本文不构成阶段4开发授权。
