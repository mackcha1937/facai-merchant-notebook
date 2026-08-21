# 05 · 测试报告

版本：v2.0-rc1 阶段1
日期：2026-08-21

## 测试结果：120 passed（V1 100 + 阶段1 新增 20）

## 新增测试

| 测试 | 覆盖 |
|---|---|
| test_stage1_tenant_rbac.py（4） | 跨租户客户/服务隔离、owner/admin 权限、默认租户 |
| test_stage1_migration.py（5） | 空库升级、downgrade 安全、租户回填、幂等、重升级 |
| test_stage1_hardening.py（11） | NOT NULL、非法外键失败、fail-closed、跨租户隔离、RBAC API、历史商品映射 |

## 覆盖的验收要求

1. V1 原有 100 个测试全部通过 ✅
2. Alembic 空库升级到最新版 ✅
3. 现有 V1 数据库 baseline + upgrade ✅
4. Migration downgrade 安全（V1 表不删）✅
5. 默认 tenant 回填 ✅
6. owner/admin 权限 ✅
7. 跨租户读取/修改/导出阻断 ✅
8. 账本余额与核销回归 ✅
9. 重复执行 Migration 幂等 ✅
10. V1 数据库内容与剩余次数未变化 ✅
11. tenant_id NOT NULL（PRAGMA）✅
12. 非法 tenant 外键写入失败 ✅
13. 缺租户上下文 fail-closed ✅
14. owner 调用 admin 接口 403、admin 通过 ✅
15. 历史 product_name 草稿映射 ✅
16. 0009 downgrade / 重新 upgrade 安全 ✅

## 命令

```bash
cd backend && .venv/bin/python -m pytest -v
```
