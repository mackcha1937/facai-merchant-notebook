# 08 · 阶段6独立审计整改

## 审计缺口与修复

1. Recommendation contract：API继续保留店主UI视图，同时为每条事项输出严格的 `contract` 投影。数据库排序分数改为0—1；原始分与理论上限只进入 `score_breakdown`。priority、权重和总边界越界直接拒绝，硬排除仍先于候选评分。Schema回归使用 Draft 2020-12 与 date-time format checker。
2. 一次性服务：`service_follow_up` 新增当前tenant的 `one_time_service` SQL来源，与套餐消费按客户/服务融合去重；只接受active服务与当前已确认知识，并复用拒绝、不适、冷却、重复等硬门禁。无有效套餐余量时保存 `remaining=null`，安全话术不显示 `None`、0次或虚构余量。
3. 稍后确认：前端增加可见日期时间输入并明确默认明天10:00。反馈原文含ISO日期或“N天后”时，`snoozed_until`留空，只由后端生成Proposal；API返回Proposal后刷新待确认列表与对话确认卡，并显示“待确认”，确认前不写提醒或客户事实。
4. AI不准确：推荐卡新增入口并强制填写说明，调用既有 `ai_inaccurate` 链路；保存匿名customer/recommendation/subject引用、evidence checksum、rule/policy version，不改变Recommendation处理状态、不在线训练、不暴露技术参数。
5. Schema漂移：`MessageDraft.updated_at` ORM改为nullable，与0019实际迁移一致；未新增Migration，未修改正式业务数据。

## 回归证据

- 阶段6定向后端：21 passed。
- 阶段6定向前端：5 passed。
- 后端全量：276 passed。
- 前端全量：47 passed / 9 files。
- Vite生产构建：79 modules transformed。
- 真实Chromium：桌面1233×750、手机390×844通过；无横向溢出，日期输入和AI不准确入口可见；“10天后再问”只生成Pending，确认前Recommendation为viewed且提醒为空。
- 正式数据库：`0019_stage6_recommendation_feedback`；`integrity_check=ok`，foreign key check无错误。
- 正式阶段6规则、推荐、话术、反馈、动作审计：均为0。
- `git diff --check`通过；敏感扫描仅命中两处明确的测试假值，无真实凭据。
- `ENABLE_V2_REAL_MODEL=false`；真实`.env`未修改。
- DeepSeek/ChatModel、外部Embedding、模型下载、外部消息发送：均为0。
