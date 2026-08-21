# 06 · 升级 / 回滚命令

版本：v2.0-rc1 阶段1
日期：2026-08-21

## 升级到最新

```bash
cd backend
.venv/bin/python -m alembic upgrade head
```

## 查看当前版本

```bash
.venv/bin/python -m alembic current
```

## 回滚（安全，不删 V1 账本）

```bash
# 回滚到 baseline（移除所有 V2 新表，保留 V1 7 张表和数据）
.venv/bin/python -m alembic downgrade 0001_baseline

# 重新升级
.venv/bin/python -m alembic upgrade head
```

## 回滚单步（示例：撤销 0008）

```bash
.venv/bin/python -m alembic downgrade 0007_recommendation
```

## 重要说明

- baseline 的 downgrade 为 pass（不删除 V1 表）；
- 0003 的 downgrade 只移除 tenant_id 列，不删账本数据；
- 回滚前建议先 `./backup.sh` 备份；
- 这些命令只在阶段1 的临时/开发库验证，正式操作前需再次确认。
