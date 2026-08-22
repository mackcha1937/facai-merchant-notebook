# 05 · Migration 与数据完整性报告

## 1. 备份

迁移前使用 SQLite 在线备份生成：

`backend/backups/app_pre_stage3_20260823_002757.db`

备份文件权限为只读，`PRAGMA integrity_check` 为 `ok`，版本为 `0014_product_unique_constraint`。

## 2. 增量迁移

- `0015_stage3_conversation_proposal`：会话唯一约束、父子外键、Proposal 幂等/过期/版本/结果字段、PendingAction 关联与索引；
- `0016_stage3_pending_read_status`：跨设备 PendingAction 阅读时间。

没有删除、重命名或覆盖 V1 权威字段。

## 3. 升降级验证

在只读备份的可写临时副本上实际执行：

```text
0014 → 0016 → 0014 → 0016
```

最终 `integrity_check=ok`，V1 数据快照完全一致。

## 4. 迁移前后对照

| 指标 | 迁移前 | 迁移后 |
|---|---:|---:|
| 客户 | 4 | 4 |
| 套餐 | 3 | 3 |
| 账本记录 | 4 | 4 |
| 有效账本记录 | 3 | 3 |
| 有效套餐总剩余 | 10 | 10 |

逐行哈希：

- customers：`5ec9d6893ea49406afe9aa298327b35fcec28b5e8b4db9f6cc4d59feb8c5453c`
- packages：`22e40d8094449bc548f0736ba7f7049f561962152db4780e062b329d16246a`
- ledger_entries：`7f43cad98276260fae448f0736ba7f7049e469f15ebae164737ff3430aa04031`

三张表迁移前、迁移后哈希逐一相同。剩余次数按有效 `package_consumption` LedgerEntry 派生。
