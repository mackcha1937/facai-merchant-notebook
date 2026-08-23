# 01 · 阶段7实现总结

阶段7已完成离线测评登记、人工工作簿、发布门槛、管理员二次确认、版本发布、回滚和审计闭环。未进入阶段8公开部署；真实模型、外部Embedding和外部消息调用均为0。

核心实现：

- 读取并校验开发包60条JSONL用例，保存用例集、草稿和Runner校验和；
- 未真实执行的用例保持 `blocked`，不把登记伪装为通过；
- CSV必须完整包含60条，`passed`和事实/安全/自然/交互四项1～5分均必填；
- 所有用例通过、49条安全关键全部通过、四项均分均不低于4.0才允许发布；
- 发布绑定草稿内容checksum、data_version和EvaluationRun，内容变化必须重新测评；
- 发布/回滚使用request_id和tenant内幂等键，保存操作人、目标版本和前后状态；
- 新版本发布后旧Release/草稿同步为superseded，回滚后双方同步为published/rolled_back；
- 店主状态只读；草稿、Run、配置正文、发布和回滚仅admin可访问。

当前停点为 `/verify/v2-stage-7` 和 `/admin/evaluations`。正式库未写入虚构草稿、测评或发布记录。
