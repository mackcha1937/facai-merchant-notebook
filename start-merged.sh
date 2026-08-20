#!/usr/bin/env bash
# 前后端合并版启动：构建前端 → 后端单服务托管前端
# 用法：./start-merged.sh  （可用 BACKEND_PORT=8000 指定端口）
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8001}"

echo "==> 构建前端（npm run build）..."
cd "$ROOT/frontend"
npm run build

echo "==> 启动合并服务（前端已由后端托管）..."
cd "$ROOT/backend"
lsof -ti :"$BACKEND_PORT" 2>/dev/null | xargs kill 2>/dev/null || true
sleep 1
nohup .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$BACKEND_PORT" \
  > /tmp/beauty-backend.log 2>&1 &
echo $! > "$ROOT/backend/.backend.pid"

sleep 2
echo ""
echo "合并版已启动，浏览器打开："
echo "  产品首页：   http://127.0.0.1:${BACKEND_PORT}/"
echo "  接口文档：   http://127.0.0.1:${BACKEND_PORT}/docs"
echo "  验收总览：   http://127.0.0.1:${BACKEND_PORT}/verify/stage-4"
echo "停止：./stop.sh （或 BACKEND_PORT=${BACKEND_PORT} ./stop.sh）"
