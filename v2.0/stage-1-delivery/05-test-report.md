# 05 · 测试报告

版本：v2.0-rc1 阶段1
日期：2026-08-21

## 测试结果：109 passed（V1 100 + 阶段1 新增 9）

## 新增测试

| 测试 | 覆盖 |
|---|---|
| test_stage1_tenant_rbac.py（4） | 跨租户客户/服务隔离、owner/admin 权限、默认租户 |
| test_stage1_migration.py（5） | 空库升级到 head、downgrade 安全、默认租户回填、幂等、重升级 |

## 覆盖的验收要求

1. V1 原有 100 个测试全部通过 ✅
2. Alembic 从空测试库升级到最新版 ✅
3. 现有 V1 数据库 baseline + upgrade ✅
4. Migration downgrade 安全（V1 表不删）✅
5. 默认 tenant 回填 ✅
6. owner/admin 权限 ✅
7. 跨租户读取/修改/导出阻断 ✅
8. 账本余额与核销回归（V1 已有测试）✅
9. 重复执行 Migration 幂等 ✅
10. 当前 V1 数据库内容与剩余次数未变化 ✅

## 命令

```bash
cd backend && .venv/bin/python -m pytest -v
```
