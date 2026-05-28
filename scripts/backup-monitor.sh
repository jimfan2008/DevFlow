#!/bin/bash
# DevFlow 备份监控脚本
# 用途：检查备份状态，发送告警通知

set -e

BACKUP_ROOT="/e/code/DevFlow/backups"
LOG_FILE="$BACKUP_ROOT/monitor.log"
ALERT_FILE="$BACKUP_ROOT/alerts.log"
MAX_BACKUP_AGE_HOURS=26  # 最大备份年龄（小时）
MIN_BACKUP_SIZE_MB=10    # 最小备份大小（MB）

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

alert() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ALERT] $1" | tee -a "$ALERT_FILE"
}

# 检查最新备份
check_latest_backup() {
    echo "检查最新备份..."
    
    latest_backup=$(ls -1t "$BACKUP_ROOT" | grep "^20" | head -1)
    
    if [ -z "$latest_backup" ]; then
        alert "❌ 未找到任何备份！"
        return 1
    fi
    
    backup_path="$BACKUP_ROOT/$latest_backup"
    backup_time=$(date -d "${latest_backup:0:8} ${latest_backup:9:2}:${latest_backup:12:2}" +%s)
    current_time=$(date +%s)
    age_hours=$(( (current_time - backup_time) / 3600 ))
    
    echo "最新备份: $latest_backup"
    echo "备份年龄: ${age_hours}小时"
    
    if [ $age_hours -gt $MAX_BACKUP_AGE_HOURS ]; then
        alert "⚠️ 备份过期！最新备份已超过 ${age_hours}小时 (阈值: ${MAX_BACKUP_AGE_HOURS}小时)"
        return 1
    fi
    
    # 检查备份大小
    backup_size=$(du -sm "$backup_path" | cut -f1)
    echo "备份大小: ${backup_size}MB"
    
    if [ $backup_size -lt $MIN_BACKUP_SIZE_MB ]; then
        alert "⚠️ 备份大小异常！仅 ${backup_size}MB (最小阈值: ${MIN_BACKUP_SIZE_MB}MB)"
        return 1
    fi
    
    echo -e "${GREEN}✅ 备份状态正常${NC}"
    return 0
}

# 检查备份文件完整性
check_backup_integrity() {
    echo ""
    echo "检查备份文件完整性..."
    
    latest_backup=$(ls -1t "$BACKUP_ROOT" | grep "^20" | head -1)
    backup_path="$BACKUP_ROOT/$latest_backup"
    
    required_files=(
        "devflow_db.sql.gz"
        "postgres_volume.tar.gz"
        "redis_volume.tar.gz"
        "gitea_data.tar.gz"
        "manifest.json"
    )
    
    missing_files=()
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$backup_path/$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        alert "❌ 备份文件不完整！缺失: ${missing_files[*]}"
        return 1
    fi
    
    # 检查压缩文件完整性
    for file in "${required_files[@]}"; do
        if [[ "$file" == *.gz ]]; then
            if ! gzip -t "$backup_path/$file" 2>/dev/null; then
                alert "❌ 压缩文件损坏: $file"
                return 1
            fi
        elif [[ "$file" == *.tar.gz ]]; then
            if ! tar tzf "$backup_path/$file" >/dev/null 2>&1; then
                alert "❌ 压缩文件损坏: $file"
                return 1
            fi
        fi
    done
    
    echo -e "${GREEN}✅ 备份文件完整${NC}"
    return 0
}

# 检查备份空间
check_backup_space() {
    echo ""
    echo "检查备份空间使用..."
    
    backup_size=$(du -sm "$BACKUP_ROOT" | cut -f1)
    backup_count=$(ls -1d "$BACKUP_ROOT"/*/ 2>/dev/null | wc -l)
    
    echo "总备份大小: ${backup_size}MB"
    echo "备份数量: $backup_count"
    
    # 检查磁盘空间
    disk_usage=$(df "$BACKUP_ROOT" | tail -1 | awk '{print $5}' | tr -d '%')
    disk_available=$(df -m "$BACKUP_ROOT" | tail -1 | awk '{print $4}')
    
    echo "磁盘使用率: ${disk_usage}%"
    echo "可用空间: ${disk_available}MB"
    
    if [ $disk_usage -gt 90 ]; then
        alert "⚠️ 磁盘空间不足！使用率 ${disk_usage}%，可用 ${disk_available}MB"
        return 1
    fi
    
    echo -e "${GREEN}✅ 磁盘空间充足${NC}"
    return 0
}

# 检查Docker容器状态
check_containers() {
    echo ""
    echo "检查Docker容器状态..."
    
    containers=(
        "devflow-postgres"
        "devflow-redis"
        "devflow-gitea"
        "devflow-backend"
    )
    
    unhealthy=()
    
    for container in "${containers[@]}"; do
        status=$(docker inspect "$container" --format='{{.State.Status}}' 2>/dev/null || echo "not found")
        
        if [ "$status" != "running" ]; then
            unhealthy+=("$container:$status")
        fi
    done
    
    if [ ${#unhealthy[@]} -gt 0 ]; then
        alert "⚠️ 容器状态异常: ${unhealthy[*]}"
        return 1
    fi
    
    echo -e "${GREEN}✅ 所有容器运行正常${NC}"
    return 0
}

# 生成报告
generate_report() {
    echo ""
    echo "========================================="
    echo "备份监控报告"
    echo "========================================="
    echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    
    # 备份统计
    latest_backup=$(ls -1t "$BACKUP_ROOT" | grep "^20" | head -1)
    backup_count=$(ls -1d "$BACKUP_ROOT"/*/ 2>/dev/null | wc -l)
    total_size=$(du -sh "$BACKUP_ROOT" | cut -f1)
    
    echo "备份统计:"
    echo "  最新备份: $latest_backup"
    echo "  备份数量: $backup_count"
    echo "  总大小: $total_size"
    echo ""
    
    # 最近5次备份
    echo "最近5次备份:"
    ls -1t "$BACKUP_ROOT" | grep "^20" | head -5 | while read backup; do
        size=$(du -sh "$BACKUP_ROOT/$backup" | cut -f1)
        echo "  $backup ($size)"
    done
    echo ""
    
    # 告警历史
    if [ -f "$ALERT_FILE" ]; then
        alert_count=$(wc -l < "$ALERT_FILE")
        echo "告警统计:"
        echo "  总告警数: $alert_count"
        echo "  最近告警:"
        tail -3 "$ALERT_FILE" | while read line; do
            echo "    $line"
        done
    fi
    
    echo "========================================="
}

# 主检查流程
main() {
    echo -e "${GREEN}=== DevFlow 备份监控 ===${NC}"
    echo ""
    
    errors=0
    
    check_latest_backup || ((errors++))
    check_backup_integrity || ((errors++))
    check_backup_space || ((errors++))
    check_containers || ((errors++))
    
    generate_report
    
    if [ $errors -gt 0 ]; then
        echo ""
        echo -e "${RED}发现 $errors 个问题，请及时处理！${NC}"
        exit 1
    else
        echo ""
        echo -e "${GREEN}✅ 所有检查通过${NC}"
        exit 0
    fi
}

main
