# 02 · SQL规则、硬排除与评分报告

## 规则边界

阶段6只读取当前 tenant、状态为 active 的最高版本规则：

- `product_repurchase`：最近一次有效商品购买距目标日达到规则天数；
- `service_follow_up`：有效套餐消费或一次性服务的最近日期达到规则间隔；两种来源按客户/服务融合去重，无套餐时余量保持 `null`；
- `package_renewal`：权威派生余量小于等于规则阈值，且日期证据有效。

规则记录包含 rule/version、policy version、conditions、hard exclusions、score config、cooldown、priority、发布人与时间。店主端没有规则写 API，也不展示权重或阈值。本阶段不建设阶段7规则发布/回滚。

## 硬排除顺序

候选进入评分前依次校验：

1. 客户、产品、服务、套餐为当前 tenant 且未删除、未停用、未合并；
2. 指定产品/服务存在 confirmed、active、published、未撤回的当前知识；
3. 只读取 confirmed、当前有效的 CustomerFact；营销拒绝和未解除的不适、刺痛、泛红、禁忌、不耐受等直接排除；
4. 店主“Do not recommend”反馈持续硬排除，直到明确 `allow_recommendation`；
5. 同客户、trigger、subject 的未处理事项直接抑制；近期已联系或已处理仍在冷却期则抑制；
6. 日期无效、余量为负、购买数量无效或结构化证据不足时拒绝生成。

未确认 CustomerFact 不进入排除或加分。硬排除原因记录在刷新结果供审计，但不会作为销售事项展示。

## 确定性评分与幂等

评分只由规则内受限数值、逾期天数、结构化证据、权威低余量和 rule priority 组成。数据库排序分数本身归一化到 0—1，原始点数与理论上限仅保存在 breakdown；priority、单项权重和总边界越界会直接拒绝规则。展示契约直接使用该归一化分数，并通过开发包 `recommendation.schema.json`（含 date-time format）自动校验。

generation key 绑定 owner、目标日期、rule ID/version、客户、trigger、subject。checksum 不变时不更新 `read_at` 或重复红点；同一日内容变化才递增 data_version 并重新标为未查看。旧日推荐保存原证据，不原地改写。
