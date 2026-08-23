# 05 · Migration 与数据完整性报告

## 1. 备份

迁移前使用 SQLite 在线备份生成：

`backend/backups/app_pre_stage4_20260823_095758.db`

备份文件权限为只读，`PRAGMA integrity_check=ok`，版本为 `0016_stage3_pending_read_status`。备份目录保持 Git 忽略，不进入提交。

## 2. 增量迁移

`0017_stage4_entity_hardening` 仅增加：

- `products.owner_id`；
- `products.merged_into_id` 自关联外键；
- 当前客户事实、产品状态、别名归一化和产品合并索引；
- 历史产品 owner 的租户店主回填与历史别名归一化。

没有删除、重命名或覆盖 V1/V2 已有权威字段。

## 3. 升降级验证

在只读备份的可写临时副本上实际执行：

```text
0016 → 0017 → 0016 → 0017
```

每次升/降级后 `integrity_check=ok`，原有表逐行快照完全一致。正式本地数据库已升级到 `0017_stage4_entity_hardening`。

## 4. 迁移前后对照

| 指标 | 迁移前 | 迁移后 |
|---|---:|---:|
| 客户 | 4 | 4 |
| 套餐 | 3 | 3 |
| 账本记录 | 4 | 4 |
| 有效账本记录 | 3 | 3 |
| 客户事实 | 0 | 0 |
| 产品 | 1 | 1 |
| 产品别名 | 0 | 0 |
| 有效套餐总剩余 | 10 | 10 |

原有数据快照哈希在迁移前、降级后和再升级后一致：

- customers：`85b033f6fd9a3ac64e09bc7c1f4ea8e3d5f06740f2645ac62ee1e404a7817c02`
- packages：`22e40d8094449bc5487fc125f11283a99f561962152db4780e062b329d16246a`
- ledger_entries：`7f43cad98276260fae448f0736ba7f7049e469f15ebae164737ff3430aa04031`
- products（旧字段）：`e0c3aa7cf18ae53958fbde4b911dce622835b85738d1282d3989d824f1454e96`

现有产品 `owner_id=1`、`merged_into_id=NULL`，说明回填成功且没有改变生命周期。
