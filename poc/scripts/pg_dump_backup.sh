#!/bin/bash
#
# PostgreSQL 自动化备份脚本
# 功能：定时备份 DevFlow 数据库，保留最近 N 天的备份
# 使用方法：./pg_dump_backup.sh [options]
#

set -e

# ==================== 配置参数 ====================
# 数据库连接配置
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-devflow_user}"
DB_NAME="${DB_NAME:-devflow_db}"
DB_PASSWORD="${DB_PASSWORD:-devflow_password}"

# 备份目录配置
BACKUP_DIR="${BACKUP_DIR:-/home/jim/DevFlow/poc/database/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

# 备份文件名格式
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/devflow_${TIMESTAMP}.sql"
COMPRESSED_FILE="${BACKUP_FILE}.gz"

# 日志文件
LOG_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ==================== 函数定义 ====================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

show_usage() {
    cat << EOF
PostgreSQL 自动化备份脚本

用法：$0 [选项]

选项:
    -h, --host      数据库主机 (默认：localhost)
    -p, --port      数据库端口 (默认：5432)
    -u, --user      数据库用户 (默认：devflow_user)
    -d, --database  数据库名称 (默认：devflow_db)
    -n, --naming    命名前缀 (默认：devflow)
    -r, --retention 保留天数 (默认：7)
    -l, --list      列出所有备份文件
    -d, --delete    删除指定日期的备份
    -c, --clean     清理所有过期备份
    -t, --test      测试备份
    -v, --verbose   详细输出
    -h, --help      显示此帮助信息

示例:
    $0                          # 使用默认配置执行备份
    $0 --retention 14           # 保留 14 天备份
    $0 --list                   # 列出所有备份
    $0 --clean                  # 清理过期备份
    $0 --test                   # 测试备份功能

EOF
}

# ==================== 主函数 ====================

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--host)
            DB_HOST="$2"
            shift 2
            ;;
        -p|--port)
            DB_PORT="$2"
            shift 2
            ;;
        -u|--user)
            DB_USER="$2"
            shift 2
            ;;
        -d|--database)
            DB_NAME="$2"
            shift 2
            ;;
        -n|--naming)
            BACKUP_NAME="$2"
            shift 2
            ;;
        -r|--retention)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        -l|--list)
            log_info "备份列表:"
            ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null || echo "无备份文件"
            exit 0
            ;;
        -c|--clean)
            log_info "清理 ${RETENTION_DAYS} 天前的备份..."
            find "$BACKUP_DIR" -name "*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete
            log_info "清理完成"
            exit 0
            ;;
        -t|--test)
            log_info "测试备份功能..."
            export PGPASSWORD="$DB_PASSWORD"
            pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" --schema-only > /dev/null 2>&1
            if [ $? -eq 0 ]; then
                log_info "备份测试成功"
                exit 0
            else
                log_error "备份测试失败"
                exit 1
            fi
            ;;
        -v|--verbose)
            set -x
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            log_error "未知选项：$1"
            show_usage
            exit 1
            ;;
    esac
done

# ==================== 执行备份 ====================

log_info "开始备份数据库：$DB_NAME"
log_info "备份文件：$COMPRESSED_FILE"

# 设置 PGPASSWORD 环境变量
export PGPASSWORD="$DB_PASSWORD"

# 执行备份
if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" --format=plain --no-owner --no-acl --verbose 2>> "$LOG_FILE" | gzip > "$COMPRESSED_FILE"; then
    BACKUP_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
    log_info "备份完成！文件大小：$BACKUP_SIZE"
    
    # 验证备份文件
    if gunzip -t "$COMPRESSED_FILE" 2>> "$LOG_FILE"; then
        log_info "备份文件验证成功"
    else
        log_error "备份文件验证失败"
        exit 1
    fi
    
    # 记录备份元数据
    echo "{
    \"filename\": \"$(basename $COMPRESSED_FILE)\",
    \"size\": \"$BACKUP_SIZE\",
    \"timestamp\": \"$(date -Iseconds)\",
    \"database\": \"$DB_NAME\",
    \"host\": \"$DB_HOST\",
    \"retention_days\": $RETENTION_DAYS
}" > "${COMPRESSED_FILE}.meta"
    
    log_info "元数据已保存"
else
    log_error "备份失败"
    exit 1
fi

# 清理过期备份
log_info "清理 ${RETENTION_DAYS} 天前的备份..."
OLD_BACKUPS=$(find "$BACKUP_DIR" -name "*.sql.gz" -type f -mtime +${RETENTION_DAYS} | wc -l)
find "$BACKUP_DIR" -name "*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete
find "$BACKUP_DIR" -name "*.sql.gz.meta" -type f -mtime +${RETENTION_DAYS} -delete
log_info "已删除 $OLD_BACKUPS 个过期备份文件"

log_info "备份任务完成！日志文件：$LOG_FILE"

# 发送通知（可选）
# curl -X POST "https://hooks.slack.com/services/YOUR/WEBHOOK/URL" -d "{\"text\":\"数据库备份完成：$COMPRESSED_FILE\"}"

exit 0
