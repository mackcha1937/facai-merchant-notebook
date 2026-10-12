# 发财·智能客户经营助手 V2

版本：v2.0 邀请内测准备版

状态：阶段 0～8 已完成；邀请内测认证和生产配置已完成本地验证，尚未购买或创建云资源

最近验收：2026-08-28

## 项目简介

“发财”是面向美容店店主的本地智能客户经营助手。在 v1 准确账本能力上，V2 增加了多日对话、客户事实、产品实体、知识库 RAG、客户跟进推荐、反馈闭环和 AI 测评发布治理。

当前版本准备面向本人和 1～3 家店进行邀请内测。已增加一次性邀请码、账号密码、HttpOnly 会话、CSRF 和多店租户隔离；尚未公开部署，也没有线上访问域名。真实 DeepSeek 模型默认关闭，只有在明确授权并手动开启后才会调用。

## 当前完成度

- 阶段 0～8 的代码、数据库迁移和交付报告已完成；
- 店主端支持对话、今日事项、客户账本、服务/产品与知识管理；
- 管理员端支持 AI 测评、版本发布、回滚和审计；
- 所有写操作通过结构化 Proposal 确认后写入；
- 具备租户隔离、角色权限、失败降级、安全响应头和 SQLite 备份恢复校验；
- 最新基线为后端 297 项、前端 64 项自动测试全部通过；
- 当前数据库迁移版本为 `0021_pilot_auth_production`；
- 生产环境要求托管 PostgreSQL，禁止使用函数实例 `/tmp` 或 SQLite 保存客户数据。

## 技术栈

```text
前端：React 18 + Vite + React Router
后端：FastAPI + SQLAlchemy + Alembic
本地数据库：SQLite；邀请内测生产库：托管 PostgreSQL（待获批创建）
对话模型：可选 DeepSeek 适配器（默认关闭真实调用）
Embedding：本地可替换适配器
运行方式：前后端分离开发，或由 FastAPI 托管前端构建产物
```

## 快速启动

推荐使用合并版，只开放一个本地端口：

```bash
./start-merged.sh
```

启动后访问：

- 产品首页：<http://127.0.0.1:8001/>
- 阶段 8 总验收：<http://127.0.0.1:8001/verify/v2-stage-8>
- V2 店主端：<http://127.0.0.1:8001/app/chat>
- V2 管理员测评台：<http://127.0.0.1:8001/admin/evaluations>
- API 文档：<http://127.0.0.1:8001/docs>

停止服务：

```bash
./stop.sh
```

完整的启动、配置、测试和备份说明见 [运行说明](./运行说明.md)。

## V2 文档与交付记录

- [V2 开发包入口](./v2.0/facai-v2-development-package/00-VSCODE-START-HERE.md)
- [V2 产品需求](./v2.0/facai-v2-development-package/01-product-requirements.md)
- [V2 前端交互规范](./v2.0/facai-v2-development-package/02-frontend-interaction-spec.md)
- [V2 后端架构](./v2.0/facai-v2-development-package/03-backend-architecture.md)
- [阶段 8 本地总验收总结](./v2.0/stage-8-delivery/01-stage-8-local-acceptance-summary.md)
- [生产准备度与已知限制](./v2.0/stage-8-delivery/07-production-readiness-known-limitations.md)
- [邀请内测上线准备报告](./v2.0/pilot-deployment/01-readiness-summary.md)
- [邀请内测部署运行手册](./v2.0/pilot-deployment/02-deployment-runbook.md)

根目录的 `01`～`05` 文档以及 `v1.0/` 目录保留为 v1 开发基线和兼容参考，不再代表当前项目进度。

## 安全边界

- API Key 只保存在 `backend/.env`，不得提交到版本库、前端或文档；
- 默认本地店主身份仅用于开发；生产启动校验会强制关闭该模式；
- SQLite 只用于本机，线上必须使用托管 PostgreSQL，并在真实云库上完成一次迁移演练；
- 如需启用真实模型、外部 Embedding、微信/短信发送或创建付费云资源，必须分别确认费用、隐私和安全方案。
