#!/bin/bash
# GBM AI Agent HR - 数据库恢复脚本
# 使用方式: bash scripts/restore.sh <backup_file>

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "[ERROR] Usage: bash scripts/restore.sh <backup_file.sql.gz>"
    exit 1
fi

BACKUP_FILE="$1"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-hr_admin}"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "[ERROR] Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "[INFO] Starting database restore at $(date)"
echo "[INFO] Restoring from: $BACKUP_FILE"

# 解压并恢复
gunzip -c "$BACKUP_FILE" | mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"${DB_PASSWORD}"

echo "[INFO] Restore completed successfully at $(date)"
