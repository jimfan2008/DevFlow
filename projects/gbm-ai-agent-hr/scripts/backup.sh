#!/bin/bash
# GBM AI Agent HR - 数据库备份脚本
# 使用方式: bash scripts/backup.sh

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/gbm-hr}"
DATE=$(date +%Y%m%d_%H%M%S)
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-hr_admin}"

mkdir -p "$BACKUP_DIR"

echo "[INFO] Starting database backup at $(date)"

# 备份 4 个 schema
for schema in hr_user hr_recruit hr_payroll hr_auto; do
    echo "[INFO] Backing up schema: $schema"
    mysqldump -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"${DB_PASSWORD}"         --single-transaction --routines --triggers         "$schema" > "$BACKUP_DIR/${schema}_${DATE}.sql" 2>/dev/null
    gzip "$BACKUP_DIR/${schema}_${DATE}.sql"
    echo "[OK] Backup completed: ${schema}_${DATE}.sql.gz"
done

# 清理超过保留期的备份
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +${BACKUP_RETENTION_DAYS:-15} -delete 2>/dev/null

echo "[INFO] Backup completed successfully at $(date)"
