#!/usr/bin/env bash
# 美容店智能客户账本 - 本地启动脚本（阶段0）
# 用法：
#   ./start.sh              # 后端默认端口 8000
#   BACKEND_PORT=8001 ./start.sh   # 若 8000 被占用，可指定其他端口
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"

echo "==> 启动后端（端口 ${BACKEND_PORT}）"
cd "$ROOT/backend"
nohup .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$BACKEND_PORT" \
  > /tmp/beauty-backend.log 2>&1 &
echo $! > "$ROOT/backend/.backend.pid"

echo "==> 启动前端（端口 5173）"
cd "$ROOT/frontend"
VITE_BACKEND_TARGET="http://127.0.0.1:${BACKEND_PORT}" \
  nohup npm run dev > /tmp/beauty-frontend.log 2>&1 &
echo $! > "$ROOT/frontend/.frontend.pid"

sleep 2
echo ""
echo "启动完成："
echo "  后端接口文档： http://127.0.0.1:${BACKEND_PORT}/docs"
echo "  前端验证页：   http://127.0.0.1:5173/verify/stage-0"
echo "  后端日志：     /tmp/beauty-backend.log"
echo "  前端日志：     /tmp/beauty-frontend.log"
echo "停止： ./stop.sh  （或 BACKEND_PORT=${BACKEND_PORT} ./stop.sh）"
