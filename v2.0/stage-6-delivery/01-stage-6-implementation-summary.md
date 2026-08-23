# 01 · 阶段6实现总结

## 交付结论

阶段6“推荐、话术和反馈”已完成，停点为 `/verify/v2-stage-6`。本阶段只建设三类 SQL 权威推荐、硬排除、确定性评分、Top3 今日事项、阶段5证据快照、本地安全话术、有限改写、店主反馈和确认前 Proposal。

没有进入阶段7评测 Runner、AI 配置发布/回滚，也没有进入阶段8。阶段6新增真实 DeepSeek/ChatModel 调用 0，外部 Embedding 调用 0，模型下载 0，外部消息发送 0；`ENABLE_V2_REAL_MODEL` 仍保持默认 false。

## 已完成能力

- `0019_stage6_recommendation_feedback` 复用 0007 已建的 `recommendation_rules`、`recommendations`、`message_drafts`、`follow_up_feedback`，只增量补齐版本、Owner、幂等、证据、状态、冲突和审计字段。
- 只支持 `product_repurchase`、`service_follow_up`、`package_renewal` 三种候选；规则必须已存在且 active，正式库不自动种规则或虚构推荐。
- 余额、购买/核销日期、客户和实体状态均从当前 tenant SQL 权威数据读取；未确认 CustomerFact 不参与正式推荐。
- 硬排除先于评分，评分保存 policy/rule version、breakdown 和稳定证据快照；硬排除不会被高分覆盖。
- 主动今日事项按客户去重，最多 Top3；其余通过 `scope=all` 查询。同 owner、日期、规则版本和实体使用稳定 generation key 幂等刷新。
- RAG 只调用阶段5本地 `retrieve`；指定实体当前知识强过滤。推荐保存 document/version/source/score/snippet 快照，旧推荐不随知识更新改写。
- 话术由本地确定性模板生成，支持“短一点”“不提购买”；复制不等于联系，没有任何发送 API 或控件。
- 今日事项逐条打开才写 `read_at`；未查看数与未处理数分离。处理、snooze、拒绝、解除拒绝和复制均有 owner/tenant、data_version、idempotency 与动作审计。
- 反馈原文可保存；从原文确定性提取的偏好或下次日期只生成统一 Proposal，确认前不写 CustomerFact、账本或提醒。

## 当前停点

阶段6代码、测试、Migration、构建和本地浏览器验收完成。等待阶段6验收，不自动开始阶段7或阶段8。
