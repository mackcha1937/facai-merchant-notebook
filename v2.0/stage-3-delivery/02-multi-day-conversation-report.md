# 02 · 多日会话报告

## 1. Thread 与 Session

数据库唯一约束保证同一 tenant、同一 owner 只有一个主 Thread。Session 使用 Asia/Shanghai 日期，唯一键为 `tenant_id + thread_id + session_date`。并发首次进入时由唯一约束兜底，重复进入返回原 Thread/Session。

## 2. 消息与历史

每条消息归属一个按日 Session，历史 API 使用消息 ID 作为向前游标，最多返回 100 条。响应携带 `session_date`，前端在日期变化处插入分隔。刷新后重新请求主 Thread、最近历史和 PendingAction，不依赖页面内 Mock。

MessageBlock 保存固定 UI Block、状态、Proposal 关联和 `data_version`。EntityMention 保存客户/服务引用。ContextSummary 保存主题、实体 ID、未完成事项 ID 和版本。

## 3. 上下文预算

上下文组装固定包含：

1. 当前输入；
2. 当前 PendingAction；
3. 最多 12 条近期相关消息；
4. 当前或最近 Session 的结构化摘要；
5. 最新权威对象快照。

返回值明确标记 `full_history_sent=false`。完整聊天历史不会整体发送给模型。

## 4. 相对日期固定

支持今天、昨天、前天、明天、后天、月底、数字或中文数字“几天后”以及显式日期。首次解析时保存：原表达、绝对日期、`Asia/Shanghai`、解析时间。跨日恢复和重新生成沿用原绝对日期，不重新解释相对词。

## 5. PendingAction 恢复

刷新和跨日进入会返回 pending、stale、expired 项。取消不写账；过期或 stale 禁止直接确认；重新生成会读取当前权威数据、创建新 Proposal，并把旧 PendingAction 标记为 regenerated。

## 6. 阅读状态

Message 和 PendingAction 的 `read_at` 均由后端保存。手机和 Web 读取同一状态；抽屉宽度、展开状态、滚动和草稿仍保存在设备本地。
