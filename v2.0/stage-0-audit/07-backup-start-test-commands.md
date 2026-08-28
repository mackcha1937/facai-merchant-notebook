# 07 · 运行 / 测试 / 备份 / 回滚命令

版本：v2.0-rc1 阶段0
日期：2026-08-21

## 运行（合并版单端口）

```bash
cd /path/to/merchant-notebook
./start-merged.sh
```

- 产品首页：http://127.0.0.1:8001/
- 阶段0 验证页：http://127.0.0.1:8001/verify/v2-stage-0
- 接口文档：http://127.0.0.1:8001/docs

## 停止

```bash
./stop.sh
# 若后端用了其他端口：BACKEND_PORT=8000 ./stop.sh
```

## 测试

```bash
cd backend && .venv/bin/python -m pytest -v
```

## 备份

```bash
./backup.sh
# 备份到 backend/backups/，带时间戳
```

## 回滚（数据库）

```bash
# 说明：用备份文件覆盖当前数据库，然后重启后端
cp backend/backups/app_20260821_133206.db backend/data/app.db
./start-merged.sh
# 注意：仅当需要时才执行覆盖；正常情况下不要覆盖当前数据库
```

## 代码回滚

```bash
git checkout <目标提交>
```

## 模型验证（阶段0）

```bash
cd backend && .venv/bin/python scripts/v2_stage0_verify_model.py
```
