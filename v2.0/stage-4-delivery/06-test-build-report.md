# 06 · 测试、构建与浏览器报告

## 1. 后端

命令：`cd backend && .venv/bin/pytest -q`

结果：205 passed。覆盖阶段1—4回归、事实候选/确认/版本/撤销、产品精确/别名/模糊/本地语义候选、最多 3 个候选、新产品+购买原子事务、合并、tenant/owner、幂等、回滚、语音转写和 Migration。

阶段4模型运行链文件共 22 项 MockModel/安全用例。本次审计新增 10 项全量用例，覆盖：Key 已配置但付费开关关闭时 Adapter 零构造、配置默认值为 false、事实值缺少证据支撑时拒绝、中文/数字产品数量的后端确定性校验、999 伪造数量拒绝、手机号/微信号/邮箱 PII 零外发与本地脱敏，以及确认/取消/候选选择零模型调用。

仅有 1 条 Starlette TestClient 弃用警告，不影响结果。pytest 通过 autouse 隔离门同时清空 Key 与关闭 `ENABLE_V2_REAL_MODEL`；只有上述用例显式注入 MockModel，没有调用外部收费模型 API。

## 2. 前端

命令：`cd frontend && npm test -- --run`

结果：38 passed，7 个测试文件全部通过。

## 3. 生产构建

命令：`cd frontend && npm run build`

结果：通过，75 个模块转换完成。Vite 仅报告现有工具链弃用提示，不影响测试或构建。

## 4. 迁移、安全与格式

- 实际 Migration 往返：`0016 → 0017 → 0016 → 0017`，通过；
- 正式本地库版本：`0017_stage4_entity_hardening`，`integrity_check=ok`；
- `git diff --check`：通过；
- 应用源码、前端产物和 V2 文档的 `sk-` 模式扫描：无真实 key 命中；
- `.env`、真实 API Key 和真实客户姓名未进入 Git、前端产物或交付文档；
- DeepSeek 运行配置未替换为 Codex。

## 5. 浏览器

真实 Chromium 完成 1470×771 桌面和 390×844 手机只读验收；阶段4验证页、真实产品匹配、产品管理、客户权威读模型、对话页和手机抽屉均通过。

## 6. DeepSeek 验证状态

- 代码运行路径：已接通；
- MockModel 自动测试：已通过；
- 当前本地状态：`configured=true`、`enabled=false`、`effective=false`；
- 真实付费 DeepSeek 请求：未执行，等待店主单独授权。
