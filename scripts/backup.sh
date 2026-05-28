#!/bin/bash
# DevFlow 自动备份脚本
# 用途：备份PostgreSQL、Redis、Gitea数据和Docker Volume

set -e

# 配置
BACKUP_ROOT="/e/code/DevFlow/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"
LOG_FILE="$BACKUP_ROOT/backup.log"
RETENTION_DAYS=7  # 保留最近7天的备份

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[WARN] $1${NC}" | tee -a "$LOG_FILE"
}

# 创建备份目录
mkdir -p "$BACKUP_DIR"
log "开始备份 - $TIMESTAMP"
log "备份目录: $BACKUP_DIR"

# 检查Docker服务
if ! docker info > /dev/null 2>&1; then
    error "Docker服务未运行"
fi

# 检查容器状态
check_container() {
    if ! docker ps --filter "name=$1" --filter "status=running" | grep -q "$1"; then
        warn "容器 $1 未运行，跳过备份"
        return 1
    fi
    return 0
}

# 1. 备份PostgreSQL数据库
backup_postgres() {
    log "备份PostgreSQL数据库..."
    
    if check_container "devflow-postgres"; then
        # SQL备份
        docker exec devflow-postgres pg_dump -U devflow_user devflow_db > "$BACKUP_DIR/devflow_db.sql" 2>&1
        
        if [ $? -eq 0 ]; then
            # 压缩SQL文件
            gzip "$BACKUP_DIR/devflow_db.sql"
            success "PostgreSQL数据库备份完成: devflow_db.sql.gz"
        else
            error "PostgreSQL数据库备份失败"
        fi
        
        # Volume备份
        docker run --rm \
            -v devflow_postgres_data:/data:ro \
            -v "/e/code/DevFlow/backups/$TIMESTAMP":/backup \
            alpine tar czf /backup/postgres_volume.tar.gz /data 2>&1
        
        if [ $? -eq 0 ]; then
            success "PostgreSQL Volume备份完成: postgres_volume.tar.gz"
        fi
    fi
}

# 2. 备份Redis数据
backup_redis() {
    log "备份Redis数据..."
    
    if check_container "devflow-redis"; then
        # 触发RDB快照
        docker exec devflow-redis redis-cli BGSAVE
        
        # 等待快照完成
        sleep 5
        
        # Volume备份
        docker run --rm \
            -v devflow_redis_data:/data:ro \
            -v "$BACKUP_DIR":/backup \
            alpine tar czf /backup/redis_volume.tar.gz /data 2>&1
        
        if [ $? -eq 0 ]; then
            success "Redis Volume备份完成: redis_volume.tar.gz"
        fi
    fi
}

# 3. 备份Gitea数据
backup_gitea() {
    log "备份Gitea数据..."
    
    if check_container "devflow-gitea"; then
        # Gitea数据Volume
        docker run --rm \
            -v devflow_gitea_data:/data:ro \
            -v "$BACKUP_DIR":/backup \
            alpine tar czf /backup/gitea_data.tar.gz /data 2>&1
        
        if [ $? -eq 0 ]; then
            success "Gitea数据备份完成: gitea_data.tar.gz"
        fi
        
        # Gitea数据库Volume
        if check_container "devflow-gitea-db"; then
            docker run --rm \
                -v devflow_gitea_db_data:/data:ro \
                -v "$BACKUP_DIR":/backup \
                alpine tar czf /backup/gitea_db_volume.tar.gz /data 2>&1
            
            if [ $? -eq 0 ]; then
                success "Gitea数据库备份完成: gitea_db_volume.tar.gz"
            fi
        fi
    fi
}

# 4. 备份环境配置
backup_config() {
    log "备份环境配置..."
    
    CONFIG_DIR="$BACKUP_DIR/config"
    mkdir -p "$CONFIG_DIR"
    
    # 备份.env文件
    if [ -f "/e/code/DevFlow/.env" ]; then
        cp "/e/code/DevFlow/.env" "$CONFIG_DIR/.env"
    fi
    
    if [ -f "/e/code/DevFlow/.env.production" ]; then
        cp "/e/code/DevFlow/.env.production" "$CONFIG_DIR/.env.production"
    fi
    
    # 备份docker-compose配置
    cp "/e/code/DevFlow/docker-compose.yml" "$CONFIG_DIR/docker-compose.yml"
    
    # 备份Nginx配置
    if [ -d "/e/code/DevFlow/docker/nginx" ]; then
        cp -r "/e/code/DevFlow/docker/nginx" "$CONFIG_DIR/nginx"
    fi
    
    success "配置文件备份完成"
}

# 5. 创建备份清单
create_manifest() {
    log "创建备份清单..."
    
    MANIFEST="$BACKUP_DIR/manifest.json"
    
    cat > "$MANIFEST" <<EOF
{
    "timestamp": "$TIMESTAMP",
    "date": "$(date '+%Y-%m-%d %H:%M:%S')",
    "version": "1.0",
    "containers": {
        "postgres": "$(docker inspect devflow-postgres --format='{{.State.Status}}' 2>/dev/null || echo 'not found')",
        "redis": "$(docker inspect devflow-redis --format='{{.State.Status}}' 2>/dev/null || echo 'not found')",
        "gitea": "$(docker inspect devflow-gitea --format='{{.State.Status}}' 2>/dev/null || echo 'not found')",
        "backend": "$(docker inspect devflow-backend --format='{{.State.Status}}' 2>/dev/null || echo 'not found')"
    },
    "files": $(ls -1 "$BACKUP_DIR" | grep -v manifest.json | jq -R . | jq -s .)
}
EOF
    
    success "备份清单创建完成: manifest.json"
}

# 6. 清理旧备份
cleanup_old_backups() {
    log "清理超过 $RETENTION_DAYS 天的旧备份..."
    
    find "$BACKUP_ROOT" -type d -name "20*" -mtime +$RETENTION_DAYS -exec rm -rf {} \; 2>/dev/null || true
    
    # 只保留最近10个备份
    cd "$BACKUP_ROOT"
    ls -1t | grep "^20" | tail -n +11 | xargs -r rm -rf
    
    success "旧备份清理完成"
}

# 7. 计算备份大小
calculate_size() {
    SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
    success "备份大小: $SIZE"
}

# 主备份流程
main() {
    backup_postgres
    backup_redis
    backup_gitea
    backup_config
    create_manifest
    calculate_size
    cleanup_old_backups
    
    log "备份完成！"
    log "备份位置: $BACKUP_DIR"
    
    # 返回备份路径供其他脚本使用
    echo "$BACKUP_DIR"
}

# 执行备份
main
