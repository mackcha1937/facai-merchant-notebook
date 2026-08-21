# 发财 V2 · 阶段0 交付：代码审计与模型能力验证

版本：v2.0-rc1 阶段0
日期：2026-08-21

## 阶段0 交付文档索引（v2.0/stage-0-audit/）

1. [01-current-system-audit.md](./stage-0-audit/01-current-system-audit.md)：现有系统审计
2. [02-v1-v2-gap-matrix.md](./stage-0-audit/02-v1-v2-gap-matrix.md)：V1/V2 差异矩阵
3. [03-database-and-migration-risk.md](./stage-0-audit/03-database-and-migration-risk.md)：数据库与迁移风险
4. [04-deepseek-capability-test.md](./stage-0-audit/04-deepseek-capability-test.md)：DeepSeek 能力验证
5. [05-embedding-and-speech-options.md](./stage-0-audit/05-embedding-and-speech-options.md)：Embedding 与语音候选
6. [06-stage-1-implementation-plan.md](./stage-0-audit/06-stage-1-implementation-plan.md)：阶段1 实施计划
7. [07-backup-start-test-commands.md](./stage-0-audit/07-backup-start-test-commands.md)：运行/测试/备份/回滚命令

---

## 1. 现有 V1 代码与能力清单

### 1.1 技术栈（实测）

- 后端：FastAPI + SQLAlchemy 2.0 + httpx + pydantic-settings，Python 3.12（uv 虚拟环境）
- 前端：React 18 + react-router-dom + Vite（TypeScript 未启用，当前为 .jsx）
- 数据库：SQLite（`backend/data/app.db`）
- 迁移：**无 Alembic**，当前用 `create_all` 建表
- 模型：DeepSeek 适配器（`infrastructure/llm/deepseek.py`）
- 测试：**100 个自动测试通过**

### 1.2 V1 已实现能力

| 能力 | 状态 |
|---|---|
| 客户/别名/服务/套餐/账本 CRUD | ✅ |
| 软删除、回收站、恢复 | ✅ |
| 权威余额（opening_used_count + 未删除核销记录 SUM） | ✅ |
| 删除/恢复核销记录后余额自动重算 | ✅ |
| 自然语言记账（对话首页 + 聊天内确认卡） | ✅ |
| 5 种操作白名单 + Proposal 确认 + 幂等 + 整组事务 | ✅ |
| 客户读模型（最后消费/概览/服务详情三级） | ✅ |
| 提示词版本管理（保存/激活/回退） | ✅ |
| 系统提示词管理页 + 阶段验证页 | ✅ |
| 前后端合并单端口托管 + 备份脚本 | ✅ |

### 1.3 V1 数据库表（7 张）

`customers`、`customer_aliases`、`services`、`packages`（opening_used_count）、`ledger_entries`（product_name 为自由文本）、`prompt_versions`、`agent_proposals`。

---

## 2. V2 需求差异矩阵（V2 新增 / 变化）

| 维度 | V1 现状 | V2 要求 | 差异类型 |
|---|---|---|---|
| 租户与身份 | 无 | Tenant + User(owner/admin) + Invite，所有表带 tenant 边界 | 新增 |
| 客户事实 CustomerFact | 无 | 事实/证据/置信度/敏感级别/版本/有效期 | 新增 |
| 产品实体 Product/ProductAlias | product_name 自由文本 | 品牌+名称+规格，别名/模糊/向量匹配，生命周期+知识状态 | 新增 |
| 知识版本/Embedding | 无 | ProductKnowledgeVersion、KnowledgeDocument、EmbeddingRecord | 新增 |
| 推荐 | 无 | 复购/回访/续卡三类，规则候选+强制过滤+评分+RAG+话术 | 新增 |
| 多日会话 | 无 | Thread/Session/Message/PendingAction/摘要/绝对日期 | 新增 |
| 语音 | 无 | SpeechToTextAdapter，转写先可见可改，共用同一确认流程 | 新增 |
| 今日事项/红点 | 无 | unresolved_count + unread_count + read_at/handled_at | 新增 |
| 角色权限 | 单一店主 | owner(业务) + admin(AI配置)，RBAC 后端强制 | 新增 |
| AI 治理 | 仅提示词版本 | 草稿→测评→发布→回滚，模型/提示词/RAG/推荐策略分别版本化 | 新增 |
| Agent 意图 | 5 种 | 增加 update_customer_facts、resolve_product、query_today_tasks 等 | 扩展 |
| UI Block 协议 | 自定义确认卡 | contracts/ui-block.schema.json 六类 Block | 重构 |
| SSE 流式 | 无 | text_delta 流式 + validated_block | 新增 |
| 降级 | 基础 | 模型/Embedding/RAG/调度分别降级，账本始终可用 | 增强 |

**结论**：V2 是在 V1 账本基础上"增量"扩展，V1 的账本、余额、确认、回收站是保留的底座，不重写。

---

## 3. 数据库与迁移风险

### 3.1 风险点

1. **无迁移工具**：V1 用 `create_all`，无 Alembic；V2 必须引入显式 Migration，否则无法安全加表/加字段。
2. **无 tenant_id**：V2 从第一天要求 Tenant 边界，需给现有表加 tenant_id 并回填默认租户。
3. **product_name 自由文本**：V1 的 `ledger_entries.product_name` 是自由文本，V2 要迁移为 Product 实体（UnclassifiedProduct 草稿映射），不能直接重命名/删除字段。
4. **不能覆盖 V1 权威字段**：`packages.opening_used_count`、`ledger_entries` 等是权威余额来源，迁移只增不删不重命名。

### 3.2 迁移策略（按 03 文档第15节）

1. 先备份（`./backup.sh`，已执行）；
2. 引入 Alembic，初始 baseline 锁定 V1 当前 schema；
3. 新增表（不重命名/删除 V1 权威字段）；
4. `product_name` 迁移为 UnclassifiedProduct 映射草稿；
5. 建立 CustomerFact 空集合（不从历史聊天自动推断）；
6. 生成读模型，化名数据验证；
7. 回滚脚本只回滚 Schema/新功能，不破坏 V1 账本。

---

## 4. DeepSeek 模型真实验证结果（已执行，严格版 6 项）

验证脚本：`backend/scripts/v2_stage0_verify_model.py`（接口受 `ENABLE_STAGE0_VERIFY` 开关 + 60秒冷却保护）

| 验证项 | 结果 | 说明 |
|---|---|---|
| 模型 ID 可用性 | ✅ 通过 | `deepseek-v4-pro` 被官方接口接受 |
| 结构化 JSON 输出 | ✅ 通过 | `response_format=json_object` + JSON Schema 全量校验 |
| 工具调用 | ✅ 通过 | 返回 tool_calls，工具名/参数正确，无副作用 |
| 流式响应 SSE | ✅ 通过 | 22 个内容增量 + [DONE] |
| 超时行为 | ✅ 通过 | 仅捕获 httpx.TimeoutException 算通过 |
| 错误模型处理 | ✅ 通过 | HTTP 400 + 明确模型不支持错误 |

**关键发现**：
1. 官方支持 `deepseek-v4-pro`、`deepseek-v4-flash`、`deepseek-v4-flash-vision-exp`；用户提供的 `deepseek-v4-pro` 真实有效。
2. `deepseek-v4-pro` 是推理模型：流式先输出 `reasoning_content`（思考）再输出 `content`（答案），`max_tokens` 需足够，否则答案为空。
3. 模型请求偶发网络抖动，后续需重试与降级。

---

## 5. SpeechToText 与 Embedding 适配器候选与取舍

### 5.1 SpeechToText 候选（阶段0 只做接口骨架，不购买服务）

| 候选 | 优点 | 缺点 | 取舍 |
|---|---|---|---|
| 浏览器 Web Speech API | 免费、零配置 | 微信 WebView 兼容性差、中文识别率一般 | 原型用，不作为生产方案 |
| 云语音（阿里云/腾讯云/百度） | 中文识别好、微信内可用 | 需开通/计费 | 生产候选，需用户确认后接入 |
| OpenAI Whisper API | 中文好 | 需 OpenAI Key、跨境 | 备选 |
| 本地 whisper.cpp | 免费离线 | 部署重、需模型文件 | 暂缓 |

**结论**：先实现 `SpeechToTextAdapter` 接口 + 一个"假转写/浏览器"占位实现；真实供应商由用户确认后再接，**不擅自购买服务**。

### 5.2 Embedding 候选

| 候选 | 优点 | 缺点 | 取舍 |
|---|---|---|---|
| 本地 bge-small-zh / bge-m3 | 免费离线、中文好 | 需本地推理、模型文件 | MVP 推荐（匿名知识量小） |
| 智谱 embedding-2/3 | 国内、中文好 | 需 API Key/计费 | 云候选 |
| 阿里云/通义 embedding | 中文好 | 需开通 | 云候选 |
| OpenAI text-embedding-3 | 通用好 | 跨境 | 备选 |

**结论**：DeepSeek 当前**不提供** Embedding 接口（不在其模型列表内）。先实现 `EmbeddingAdapter` + `VectorStore` 接口骨架；MVP 用本地 bge 或用户确认后的云服务，均不接真实客户数据（只对确认后的知识卡做向量化）。

---

## 6. 本地运行 / 测试 / 备份 / 回滚命令

```bash
# 运行（合并版单端口）
cd /Users/zzymima0000/Desktop/个人项目-商家记事本
./start-merged.sh

# 测试
cd backend && .venv/bin/python -m pytest -v

# 备份
./backup.sh          # 备份到 backend/backups/

# 回滚（数据库）
# 从 backend/backups/ 取最近备份文件覆盖 backend/data/app.db 后重启
# 代码回滚：git checkout 到目标提交
```

---

## 7. 阶段1 实施计划（预告，本轮不做）

1. 引入 Alembic + Tenant/User/Invite 表 + 现有表加 tenant_id（回填默认租户）。
2. 新增 CustomerFact、Product/ProductAlias、KnowledgeVersion、Conversation、Recommendation、Release 等表。
3. owner/admin RBAC 骨架 + 种子数据（data/ 目录）。
4. `product_name` 迁移为 UnclassifiedProduct 草稿。
5. V1 账本回归测试全绿。
6. `/verify/v2-stage-1` 验证页。

---

阶段0 完成，已暂停。
