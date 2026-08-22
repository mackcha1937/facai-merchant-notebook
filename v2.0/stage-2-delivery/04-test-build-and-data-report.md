# 04 · 阶段2测试、构建与数据报告

版本：v2.0-rc1 阶段2
归档日期：2026-08-23
验证提交：`1cac323`

## 1. 自动测试结果

### 后端

实际命令：

```bash
cd backend
.venv/bin/python -m pytest -q
```

实际结果：

```text
145 passed, 1 warning in 5.36s
```

说明：阶段1最终基线为135项；阶段2新增10项后，后端全量为145项。
警告来自Starlette TestClient对当前httpx接口的弃用提示，不影响本次通过结论。

### 前端

实际命令：

```bash
cd frontend
npm test -- --run
```

实际结果：

```text
Test Files  5 passed (5)
Tests       29 passed (29)
```

后端145项＋前端29项，合计174项通过。

## 2. 前端正式构建

实际命令：

```bash
cd frontend
npm run build
```

实际结果：

```text
vite v5.4.21
73 modules transformed
build succeeded
```

构建产物生成成功。前端测试运行时存在Vite插件配置弃用警告，不影响测试和构建结果，
后续依赖升级时应单独处理。

## 3. Migration与数据库状态

- 当前Migration：`0014_product_unique_constraint`；
- 当前数据库完整性检查：`ok`；
- 当前业务库共38张业务及迁移相关表；
- 当前V1基线计数与阶段1记录一致：4个客户、3个套餐、4条账本记录，其中3条未删除；
- 阶段2没有新增Migration，没有修改ORM业务表结构，没有运行阶段3数据迁移。

## 4. 阶段2前后数据一致性

本次接管审计使用阶段2开始前备份
`backend/backups/app_20260822_103933.db` 与当前 `backend/data/app.db` 进行只读比较：

- 两库Migration版本均为 `0014_product_unique_constraint`；
- `customers`、`customer_aliases`、`services`、`packages`、`ledger_entries`、
  `prompt_versions`、`agent_proposals` 七张V1表逐行双向差集均为0；
- 两库全库 `data-only` 摘要一致；
- 重新运行145项后端测试前后，当前数据库 `data-only` 摘要没有变化。

结论：没有发现阶段2污染或改写真实V1数据库数据。

阶段2自带测试会在调用只读状态和Mock语音接口前后比较V1表计数；
本次独立审计进一步使用阶段开始前备份完成逐行和全库逻辑数据对照。

## 5. API Key安全检查

- 版本库只跟踪 `backend/.env.example`，密钥值为空；
- 本地 `backend/.env` 受 `.gitignore` 规则保护；
- 未在已跟踪文件中发现长格式密钥值；
- 正式前端构建产物未发现密钥赋值或长密钥模式；
- 阶段2状态接口和Mock语音接口不返回密钥；
- 文档、测试输出和本报告均未记录任何真实密钥。

仓库中的密钥格式字符串仅用于脱敏测试或配置占位，不是真实凭证。

## 6. 客户信息安全检查

- 阶段2V2 fixture全部声明为合成Mock数据并标记 `is_mock=true`；
- V2前端fixture不含手机号、微信号或微信标识字段值；
- 正式前端构建产物未发现11位手机号模式；
- 后端阶段2状态接口只返回计数和摘要，不返回客户姓名或其他身份字段；
- 数据库一致性核验使用摘要和差集计数，没有输出客户记录内容。

结论：未发现阶段2泄露API Key、手机号、微信标识或可确认的真实客户姓名。

## 7. 测试边界

29项前端测试主要覆盖组件、纯ContextStack逻辑、Mock语音状态机、今日事项逻辑和Mock数据安全。
它们没有完整覆盖真实AppShell浏览器history、焦点陷阱、焦点恢复、左滑关闭和页面刷新恢复。
这些项目不能仅凭当前自动测试标记为通过，具体结论以 `02-interaction-acceptance-report.md` 为准。
