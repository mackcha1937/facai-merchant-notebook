# 邀请内测部署运行手册

本手册是下一步云上执行清单，不代表这些资源已经创建。执行顺序遵循“先预算和安全确认，再创建资源”。

## 1. 资源方案

- 一个 veFaaS/FastAPI 应用：同时提供静态前端和 `/api`；
- 一个 API 网关 HTTPS 入口；
- 一个与应用同地域、同 VPC 的托管 PostgreSQL；
- 云日志、基础告警和数据库自动备份；
- 初期一个应用实例或最小保留实例，服务 1～3 家店。

不使用：函数 `/tmp` 持久化、外部 Embedding、自动微信/短信发送、真实 DeepSeek 默认调用。

## 2. 费用闸门

在控制台确认 veFaaS、API 网关、PostgreSQL、流量、日志和备份的实时价格，形成月度上限。用户明确同意资源清单与预算后，才执行创建。

## 3. 数据库先行

1. 创建私网 PostgreSQL、专用数据库和最小权限应用用户；
2. 强制 TLS，安全组只允许应用子网；
3. 在一次性运维任务注入 `DATABASE_URL`，执行 `alembic upgrade head`；
4. 验证 head 为 `0021_pilot_auth_production`、外键有效、跨 tenant 零泄漏；
5. 开启自动备份并实际恢复到临时实例一次；
6. 禁止在正式库执行 `app.seed`。

## 4. 应用环境变量

必须项：`APP_ENV=production`、`LOCAL_DEV_OWNER_ENABLED=false`、`AUTO_CREATE_SCHEMA=false`、`DATABASE_URL`、`SESSION_SECRET`、`SESSION_COOKIE_NAME=__Host-facai_session`、`COOKIE_SECURE=true`、`EXPOSE_API_DOCS=false`、`ALLOWED_HOSTS`。

保持关闭：`ENABLE_V2_REAL_MODEL=false`、`ENABLE_STAGE0_VERIFY=false`、`ENABLE_STAGE1_VERIFY=false`、`ENABLE_STAGE2_VERIFY=false`。

由网关/平台代理确定 `FORWARDED_ALLOW_IPS`；不得无审计地信任任意公网代理。所有秘密通过平台密钥或加密环境变量注入，不写真实 `.env`。

## 5. 发布

1. 本地执行后端全量、前端全量和生产构建；
2. 使用 `.vefaasignore` 排除 `.env`、数据库、备份、测试和源码型非运行资产；
3. 在应用实例启动前执行 `python scripts/check_production_readiness.py`；
4. 由 `scripts/start_production.sh` 启动 Uvicorn；
5. API 网关只暴露 HTTPS，启用合理限流；
6. 首次只生成本人 admin 邀请码，再为每家店单独生成 owner 邀请码；
7. 邀请码通过可信的点对点渠道交付，兑换后立即失效。

## 6. 上线烟测

- 首页匿名可读；业务、管理员和验收页未登录时跳转 `/login`；
- 无会话业务 API 返回 401；错误 CSRF 返回 403；
- A 店创建的虚构客户在 B 店列表、搜索、RAG、推荐中均不可见；
- 打开列表不会批量清未读；确认前无权威账本写入；
- `/docs`、`/redoc`、`/openapi.json` 在线上关闭；
- 响应含 request ID、安全头、API no-store；日志不含 Cookie、邀请码、数据库密码或 Key；
- 真实模型、外部 Embedding、外部消息发送计数均为 0。

## 7. 回滚与停机

- 应用回滚：切回上一应用版本，不自动执行数据库 downgrade；
- 数据回滚：优先时间点恢复到新实例，核验后切换连接；
- 账号泄露：停用 User、撤销 AuthSession、轮换 Session Secret；
- 发现跨租户或秘密泄露：立即关闭公网入口，保留脱敏审计证据并通知受影响内测店。

## 8. 当前已知限制

- 尚未在真实托管 PostgreSQL、veFaaS 与 API 网关上演练；
- 未建设 MFA、找回密码、自助店铺管理和会话设备列表；
- 账号不存在时的分布式 IP 限速依赖 API 网关；应用层仅有账号失败锁定；
- 未做正式渗透测试和多实例压测；
- 旧版 PostgreSQL 历史迁移只以静态兼容和 SQLite 全链回归验证，必须以真实空库升级结果作为放行条件。
