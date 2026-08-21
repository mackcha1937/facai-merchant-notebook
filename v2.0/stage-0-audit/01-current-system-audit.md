# 01 · 现有系统审计

版本：v2.0-rc1 阶段0
日期：2026-08-21

## 1. 技术栈（实测）

- 后端：FastAPI + SQLAlchemy 2.0 + httpx + pydantic-settings，Python 3.12（uv 虚拟环境）
- 前端：React 18 + react-router-dom + Vite（当前 .jsx，未启用 TypeScript）
- 数据库：SQLite（`backend/data/app.db`）
- 迁移：**无 Alembic**，当前用 `create_all` 建表
- 模型：DeepSeek 适配器（`infrastructure/llm/deepseek.py`）
- 测试：**100 个自动测试通过**

## 2. V1 已实现能力

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

## 3. V1 数据库表（7 张）

`customers`、`customer_aliases`、`services`、`packages`（opening_used_count）、`ledger_entries`（product_name 为自由文本）、`prompt_versions`、`agent_proposals`。

## 4. 现有文件分层

- `backend/app/api/routes/`：HTTP 路由
- `backend/app/application/`：用例编排
- `backend/app/domain/`：业务规则
- `backend/app/repositories/`：数据访问
- `backend/app/agent/`：Agent 解析、白名单、匹配、提示词加载
- `backend/app/infrastructure/`：SQLAlchemy 模型、DeepSeek 适配器
- `frontend/src/pages/v1/`：V1 页面（对话、客户 Sheet、设置等）
- `frontend/src/components/v1/`：V1 组件
- `backend/tests/`：100 个测试

## 5. 启动与运维

- 合并版单端口：`./start-merged.sh`（后端托管前端 dist）
- 备份：`./backup.sh`
- 停止：`./stop.sh`
