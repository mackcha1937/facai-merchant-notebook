#!/usr/bin/env bash
# 美容店智能客户账本 - 停止脚本（只停本项目，不会影响其他项目）
# 用法：./stop.sh  或  BACKEND_PORT=8001 ./stop.sh
BACKEND_PORT="${BACKEND_PORT:-8000}"

stop_by_port() {
  local port="$1" name="$2"
  local pids
  pids="$(lsof -ti :"$port" 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    kill $pids 2>/dev/null || true
    echo "${name}已停止（端口 ${port}）"
  else
    echo "${name}未在运行（端口 ${port}）"
  fi
}

stop_by_port "$BACKEND_PORT" "后端"
stop_by_port 5173 "前端"
