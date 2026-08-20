#!/usr/bin/env bash
# 本地数据库备份脚本：把 backend/data/app.db 复制到 backend/backups/（带时间戳）
ROOT="$(cd "$(dirname "$0")" && pwd)"
DB="$ROOT/backend/data/app.db"
BACKUP_DIR="$ROOT/backend/backups"

if [ ! -f "$DB" ]; then
  echo "未找到数据库文件：$DB"
  exit 1
fi

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
DEST="$BACKUP_DIR/app_$STAMP.db"
cp "$DB" "$DEST"
echo "数据库已备份到：$DEST"
