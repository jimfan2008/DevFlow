#!/bin/bash
# DevFlow 数据恢复脚本
# 用途：从备份恢复PostgreSQL、Redis、Gitea数据

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查备份目录
if [ -z "$1" ]; then
    echo -e "${RED}用法: $0 <备份目录路径>${NC}"
    echo "示例: $0 /e/code/DevFlow/backups/20260525_120000"
    exit 1
fi

BACKUP_DIR="$1"
LOG_FILE="$BACKUP_DIR/restore.log"

if [ ! -d "$BACKUP_DIR" ]; then
    echo -e "${RED}错误: 备份目录不存在: $BACKUP_DIR${NC}"
    exit 1
fi

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[WARN] $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

log "开始从备份恢复: $BACKUP_DIR"

# 显示备份信息
if [ -f "$BACKUP_DIR/manifest.json" ]; then
    echo ""
    echo "备份信息:"
    cat "$BACKUP_DIR/manifest.json" | jq -C .
    echo ""
fi

# 确认恢复
read -p "确定要恢复此备份吗？这将覆盖当前数据！(yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "取消恢复"
    exit 0
fi

# 停止服务
log "停止Docker服务..."
docker-compose stop backend celery-worker celery-beat nginx

# 1. 恢复PostgreSQL
restore_postgres() {
    log "恢复PostgreSQL数据库..."
    
    # 恢复SQL备份
    if [ -f "$BACKUP_DIR/devflow_db.sql.gz" ]; then
        gunzip -c "$BACKUP_DIR/devflow_db.sql.gz" > /tmp/devflow_db.sql
        
        # 删除现有数据库
        docker exec devflow-postgres psql -U devflow_user -d postgres -c "DROP DATABASE IF EXISTS devflow_db;"
        docker exec devflow-postgres psql -U devflow_user -d postgres -c "CREATE DATABASE devflow_db;"
        
        # 恢复数据库
        docker exec -i devflow-postgres psql -U devflow_user devflow_db < /tmp/devflow_db.sql
        
        rm /tmp/devflow_db.sql
        success "PostgreSQL数据库恢复完成"
    elif [ -f "$BACKUP_DIR/devflow_db.sql" ]; then
        # 删除现有数据库
        docker exec devflow-postgres psql -U devflow_user -d postgres -c "DROP DATABASE IF EXISTS devflow_db;"
        docker exec devflow-postgres psql -U devflow_user -d postgres -c "CREATE DATABASE devflow_db;"
        
        docker exec -i devflow-postgres psql -U devflow_user devflow_db < "$BACKUP_DIR/devflow_db.sql"
        success "PostgreSQL数据库恢复完成"
    fi
    
    # 恢复Volume（更彻底的恢复）
    if [ -f "$BACKUP_DIR/postgres_volume.tar.gz" ]; then
        warn "恢复PostgreSQL Volume会完全覆盖数据"
        read -p "是否恢复Volume？(yes/no): " vol_confirm
        
        if [ "$vol_confirm" == "yes" ]; then
            # 停止postgres容器
            docker stop devflow-postgres
            
            # 恢复Volume数据
            docker run --rm \
                -v devflow_postgres_data:/data \
                -v "$BACKUP_DIR":/backup \
                alpine sh -c "rm -rf /data/* && tar xzf /backup/postgres_volume.tar.gz -C /"
            
            # 启动postgres容器
            docker start devflow-postgres
            sleep 10
            
            success "PostgreSQL Volume恢复完成"
        fi
    fi
}

# 2. 恢复Redis
restore_redis() {
    log "恢复Redis数据..."
    
    if [ -f "$BACKUP_DIR/redis_volume.tar.gz" ]; then
        # 停止redis容器
        docker stop devflow-redis
        
        # 恢复Volume数据
        docker run --rm \
            -v devflow_redis_data:/data \
            -v "$BACKUP_DIR":/backup \
            alpine sh -c "rm -rf /data/* && tar xzf /backup/redis_volume.tar.gz -C /"
        
        # 启动redis容器
        docker start devflow-redis
        sleep 5
        
        success "Redis数据恢复完成"
    fi
}

# 3. 恢复Gitea
restore_gitea() {
    log "恢复Gitea数据..."
    
    if [ -f "$BACKUP_DIR/gitea_data.tar.gz" ]; then
        # 停止gitea容器
        docker stop devflow-gitea
        
        # 恢复Gitea数据
        docker run --rm \
            -v devflow_gitea_data:/data \
            -v "$BACKUP_DIR":/backup \
            alpine sh -c "rm -rf /data/* && tar xzf /backup/gitea_data.tar.gz -C /"
        
        # 启动gitea容器
        docker start devflow-gitea
        sleep 10
        
        success "Gitea数据恢复完成"
    fi
    
    if [ -f "$BACKUP_DIR/gitea_db_volume.tar.gz" ]; then
        # 停止gitea-db容器
        docker stop devflow-gitea-db
        
        # 恢复Gitea数据库
        docker run --rm \
            -v devflow_gitea_db_data:/data \
            -v "$BACKUP_DIR":/backup \
            alpine sh -c "rm -rf /data/* && tar xzf /backup/gitea_db_volume.tar.gz -C /"
        
        # 启动gitea-db容器
        docker start devflow-gitea-db
        sleep 10
        
        success "Gitea数据库恢复完成"
    fi
}

# 4. 恢复配置
restore_config() {
    log "恢复配置文件..."
    
    if [ -d "$BACKUP_DIR/config" ]; then
        PROJECT_ROOT="/e/code/DevFlow"
        
        # 恢复.env文件
        if [ -f "$BACKUP_DIR/config/.env" ]; then
            cp "$BACKUP_DIR/config/.env" "$PROJECT_ROOT/.env"
        fi
        
        if [ -f "$BACKUP_DIR/config/.env.production" ]; then
            cp "$BACKUP_DIR/config/.env.production" "$PROJECT_ROOT/.env.production"
        fi
        
        # 恢复docker-compose配置
        if [ -f "$BACKUP_DIR/config/docker-compose.yml" ]; then
            cp "$BACKUP_DIR/config/docker-compose.yml" "$PROJECT_ROOT/docker-compose.yml"
        fi
        
        # 恢复Nginx配置
        if [ -d "$BACKUP_DIR/config/nginx" ]; then
            cp -r "$BACKUP_DIR/config/nginx" "$PROJECT_ROOT/docker/nginx"
        fi
        
        success "配置文件恢复完成"
    fi
}

# 执行恢复
restore_postgres
restore_redis
restore_gitea
restore_config

# 启动服务
log "启动Docker服务..."
docker-compose up -d

log "恢复完成！"
success "所有数据已从备份恢复"

# 验证服务
sleep 10
log "验证服务状态..."
docker ps --filter "name=devflow" --format "table {{.Names}}\t{{.Status}}"
