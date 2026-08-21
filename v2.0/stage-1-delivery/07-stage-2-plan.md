# 07 · 阶段2 计划

版本：v2.0-rc1 阶段1
日期：2026-08-21

> 本文件为计划预告，阶段1 未实现任何阶段2 内容。

## 阶段2 目标（按 07-development-roadmap 文档）

双端应用壳与闭环：
- 手机顶部今日事项、左侧精简入口、全部客户；
- Web 左栏 / 主对话 / 右侧工作区；
- UI Block、ContextStack、返回、收起、草稿、系统返回键；
- 语音转写可见和等价操作接口；
- 使用 Mock 数据，不接推荐。

## 阶段2 依赖（阶段1 已就绪）

- 会话相关表（conversation_threads/sessions/messages/message_blocks/entity_mentions/pending_actions/context_summaries/voice_turns）已建。
- tenant 上下文与 RBAC 骨架已就绪。
- 客户读模型（V1）可复用。

## 阶段2 将做

1. `/app/chat`、`/app/customers`、`/app/manage` 应用壳与底部导航/左栏。
2. 今日事项（Recommendation/Task 的 unread/read 状态）骨架。
3. UI Block 渲染（contracts/ui-block.schema.json 六类）。
4. 语音转写接口骨架（VoiceTurn + SpeechToTextAdapter 占位）。
5. ContextStack 返回/收起/草稿恢复。
6. 用 Mock 数据验证，不接真实推荐。

## 阶段2 验收（预告）

- 手机/电脑双端应用壳可用；
- 今日事项红点/数字正确；
- 客户列表进入详情逐层返回恢复状态；
- 语音转写可见可改；
- 不接推荐、不接真实 Embedding。
