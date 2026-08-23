# 06 · 测试、构建与浏览器报告

## 1. 后端

命令：`cd backend && .venv/bin/pytest -q`

结果：224 passed。覆盖阶段1—4回归、事实候选/确认/版本/撤销、产品精确/别名/模糊/本地语义候选、最多 3 个候选、新产品+购买原子事务、合并、tenant/owner、幂等、回滚、语音转写和 Migration。

既有阶段3 API 设备冲突用例改为在当前测试时刻创建 Proposal，消除固定历史时刻跨过 24 小时有效期后误测为“过期”的时间依赖；业务代码未改变。

阶段4模型运行链文件共 39 项 MockModel/安全用例；新增的 DeepSeek Adapter 契约文件共 2 项 MockTransport 用例。本次离线协议整改验证 JSON 非思考请求 payload、完整合法 JSON 提示词示例，以及成功响应/HTTP 错误均不泄露测试 Key。所有自动测试均未访问真实网络。

仅有 1 条 Starlette TestClient 弃用警告，不影响结果。pytest 通过 autouse 隔离门同时清空 Key 与关闭 `ENABLE_V2_REAL_MODEL`；只有上述用例显式注入 MockModel，没有调用外部收费模型 API。

## 2. 前端

命令：`cd frontend && npm test -- --run`

结果：39 passed，7 个测试文件全部通过。新增阶段4页静态验收状态用例，验证隔离验收通过、累计调用 2 次，同时常驻模型保持未生效。

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
- 隔离真实请求累计：2 次，均 HTTP 200；
- 第 1 次：候选为 `rejected_fallback`，随后由 `6d44e42` 完成 JSON Output / non-thinking 离线协议整改；
- 第 2 次：`model_runtime.attempted=true`、`status=validated`、`intent=product_purchase`，阶段4隔离真实验收通过；
- 安全结果：确认前 CustomerFact / Product / LedgerEntry 均 0 写入，仅保留 1 个 `resolving` Proposal；
- 当前常驻状态仍为 `enabled=false`、`effective=false`。本次验收记录收尾新增真实请求 0 次。
