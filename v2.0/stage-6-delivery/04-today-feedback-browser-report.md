# 04 · 今日事项、反馈与真实浏览器报告

## 今日事项与反馈闭环

- 状态支持 `new / viewed / contacted / snoozed / repurchased / not_needed / unsuitable / do_not_recommend / cancelled / expired`，并提供明确解除拒绝动作。
- `unread_count` 只看 `read_at`；`unresolved_count` 只看未处理事项。打开列表不批量清零，逐条打开才标记该条已读。
- snooze 接收绝对时间，后端统一存 UTC、前端按 `Asia/Shanghai` 展示；到期前不出现，到期后恢复为未处理事项。
- 状态动作记录 handled/contacted/snoozed 时间、data version、idempotency key 和前后状态审计。
- 反馈状态更新不调用模型。自由文本中的偏好和日期只生成 Proposal；确认前 `CustomerFact`、账本和 `next_reminder_at` 为零写入。
- AI 不准确反馈只保存匿名 customer/recommendation 引用、entity、evidence checksum 和 rule version；秘密或技术提示注入文本整体拒绝。

## 真实 Chromium 验收

使用 `/private/tmp` 隔离 SQLite 和开发包虚构客户、产品、服务、知识资料。隔离库显式装载 3 条 active 规则并生成 4 条推荐，主动列表按客户去重展示 3 位；正式库未装载这些数据。

- 桌面 1440×1000：顶部今日事项显示“3”和“新”，列表初始 `未处理3 / 未查看3`；打开一条后仅该条已读，变为 `未处理3 / 未查看2`。证据、风险、复制话术、“短一点”“不提购买”和七种反馈按钮可见，发送控件 0，无横向溢出。
- 手机 390×844：验证页和主应用 `scrollWidth=viewport=390`；顶部数字/红点、3张事项卡和详情证据可读。再打开一条后仅该条已读，`未处理3 / 未查看1`；发送控件 0。
- 浏览器只执行 GET 和两次单条 `read`；未点击复制、改写、反馈、确认或任何业务处理。

浏览器结束时隔离库：CustomerFact 0、FollowUpFeedback 0、AgentProposal 0；原有 3 条虚构账本记录未变化。仅新增 2 条逐条阅读审计，Recommendation 状态为 2 new / 2 viewed，`integrity_check=ok`、foreign key check 无错误。

## 独立整改复验

- 隔离库重新生成4条虚构Recommendation，DeepSeek/ChatModel、外部Embedding和消息发送仍为0。
- 桌面1233×750：日期时间输入与“AI不准确”入口各1个；页面 `scrollWidth == clientWidth`；规则参数与发送控件均为0。
- 输入“10天后再问”点击“稍后”后，页面显示“已生成待确认事项”；Pending新增1条，原Recommendation保持 `viewed` 且 `snoozed_until=null`。
- 手机390×844：日期输入、“AI不准确”、待确认提示均可见；`scrollWidth == clientWidth == 390`，发送控件0。
- 验收结束后隔离Chromium、8002服务及 `/private/tmp` 隔离数据库均已关闭/删除；正式库未写入虚构数据。
