# 发财 V2 邀请内测上线准备报告

日期：2026-10-12

目标范围：本人和 1～3 家受邀店铺；每店独立 tenant；个人实名认证云账号；合并式 React + FastAPI 应用。

## 当前结论

代码已达到“可以进入云资源创建与实库演练”的状态，但还没有上线，暂时没有公网使用链接。

已完成：

- 一次性邀请码开通、登录、退出、密码 scrypt 哈希、失败锁定；
- HttpOnly + SameSite=Strict + Secure 会话 Cookie，双提交 CSRF；
- 认证中间件从服务端会话建立 tenant/user/role，上游请求不能自行指定 tenant；
- 未登录业务 API 统一 401，管理员写接口继续由后端 RBAC 强制；
- 生产配置 fail-closed：拒绝 SQLite、本地默认身份、弱 Secret、非 Secure Cookie、开放 API 文档和通配 Host；
- PostgreSQL 连接驱动和历史升级路径兼容处理；
- 生产进程只读检查 Alembic head，不在多实例启动时自动迁移；
- 全部前端业务页、管理员页和验收页均要求登录；
- API 响应 no-store、安全头和 request ID；DeepSeek、外部 Embedding、外部发送仍默认关闭。

## 仍需在付费/云操作前确认

1. 目标地域、API 网关和 veFaaS 套餐的控制台实时价格；
2. 托管 PostgreSQL 的最小规格、备份保留、VPC 和 TLS 配置；
3. 用户明确批准预计月预算和将要创建的资源清单；
4. 在新建空 PostgreSQL 上完整执行 `alembic upgrade head`、0021 往返、外键和租户隔离回归；
5. 生产域名、HTTPS、限流、日志告警和备份恢复演练；
6. 自有域名上线前按控制台提示核实备案与合规要求。

## 不应照搬原文章的部分

- veFaaS `/tmp` 是临时文件系统，不能承载 SQLite 客户账本；
- 本项目是一个 FastAPI 托管 Vite 构建产物的合并应用，不是两套 Next.js；
- AK/SK、数据库密码、Session Secret 和 DeepSeek Key 不进入代码、Git、聊天或前端；
- 云资源创建、真实模型调用和任何外部发送都需要单独授权。

## 本地验证基线

- 后端：297 passed；
- 前端：13 files / 64 passed；
- 生产构建：89 modules；
- Migration head：`0021_pilot_auth_production`；
- 正式本地库和临时副本的 0021 升级→降级→升级通过，核心数据摘要一致，integrity / foreign key 均通过；
- Chromium 登录页在桌面 1440 与手机 390 宽均无横向溢出，邀请码表单与首页入口通过；
- 真实 DeepSeek、外部 Embedding、外部发送、云资源创建：本轮均为 0。
