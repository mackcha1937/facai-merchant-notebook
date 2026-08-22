# 06 · 测试与构建报告

## 1. 后端

命令：`cd backend && .venv/bin/pytest -q --disable-warnings`

结果：168 passed。覆盖阶段1、阶段2回归以及阶段3 Thread、Session、游标、日期、PendingAction、事务、幂等、并发、stale、tenant、SSE、Migration 和数据完整性。

测试没有调用外部收费模型 API。

## 2. 前端

命令：`cd frontend && npm test -- --run`

结果：34 passed，6 个测试文件全部通过。

## 3. 生产构建

命令：`cd frontend && npm run build`

结果：通过，74 个模块转换完成。Vite 仅报告现有测试工具链的 esbuild/oxc 弃用提示，不影响测试或构建结果。

## 4. 安全与格式

- `git diff --check`：通过；
- 应用源码、前端产物、V2 交付文档的 `sk-` 模式扫描：无命中；
- 仓库唯一模式命中位于既有 `backend/tests/test_sanitize.py`，内容是用于验证日志脱敏的虚构 key；
- `.env`、真实 API Key、真实客户姓名未写入 Git、前端产物或交付文档；
- DeepSeek 运行配置未替换为 Codex。

## 5. 浏览器

真实 Chromium 验收结果见 `04-frontend-interaction-acceptance-report.md`。SSE 请求、消息持久化和刷新恢复已在当前生产构建上复验；没有执行的真实数据写入明确标记为未验证，并由隔离数据库业务测试覆盖。
