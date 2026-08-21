# 03 · 租户与 RBAC 报告

版本：v2.0-rc1 阶段1
日期：2026-08-21

## 租户上下文（fail-closed）

- `app/core/tenant.py`：ContextVar 保存当前租户/角色，**不静默默认 tenant=1**；缺少上下文时按 fail-closed 拒绝。
- 开发环境：`local_dev_owner_enabled=true` + `local_default_tenant_id=1` + `local_default_owner_role=owner`（服务端配置，不接受客户端 X-Tenant-ID 冒充）。
- 生产环境：`local_dev_owner_enabled=false`，缺上下文直接拒绝。
- 所有业务仓储查询强制带 `tenant_id` 过滤（customers/services/packages/ledger/prompts/proposals/trash/读模型）。
- **禁止先按对象 ID 查询再在应用层判断租户**：get 查询在 SQL 层直接按 tenant_id 过滤。

## 默认租户与 owner

- 迁移 0003 创建默认租户（id=1「默认店铺」）和默认 owner（id=1，role=owner）。
- 现有 4 个客户回填 tenant_id=1，无空值。

## RBAC（app/core/rbac.py，已接入 API）

- `require_owner()`：业务写操作（客户/套餐/账本），owner/admin 可做；
- `require_admin()`：AI 配置操作（提示词保存/激活），仅 admin；
- 前端隐藏不算权限，后端校验强制；
- owner 调用 admin 接口返回 400（DomainError），admin 调用管理接口通过；
- 缺上下文 fail-closed（生产环境拒绝）。

## 测试结果

- owner/admin 权限测试：通过。
- 跨租户隔离：租户1 读不到租户2 的客户/服务（get 返回 None）；跨租户 ID 枚举被阻断。
- 测试文件：`tests/test_stage1_tenant_rbac.py`。
