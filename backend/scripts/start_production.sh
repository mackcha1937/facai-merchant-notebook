#!/usr/bin/env sh
set -eu

# 数据库迁移必须在发布前作为一次性步骤执行；应用实例只做只读预检，避免并发迁移。
python scripts/check_production_readiness.py
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers \
  --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}"
