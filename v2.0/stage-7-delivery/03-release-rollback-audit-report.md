# 03 · 发布、回滚与审计报告

发布前强制校验：admin权限、tenant、Run与草稿关联、完整门槛、草稿data_version、当前内容checksum和精确 `PUBLISH-{draft_id}-{checksum前8位}` 确认文本。

每个Release保存：

- source_draft_id；
- evaluation_run_id；
- published_by；
- 版本和不可变配置快照；
- published/superseded/rolled_back状态和时间。

回滚只允许当前published版本恢复同类型上一superseded版本，并要求精确 `ROLLBACK-{type}-{release_id}`。首个版本没有上一版时不展示回滚入口。发布与回滚都以tenant+idempotency_key去重；同键换目标会冲突，重试原请求返回原结果且不新增Release或审计。

管理员列表不返回配置正文、Key、完整提示词或审计前后配置内容。店主状态接口只返回脱敏汇总。
