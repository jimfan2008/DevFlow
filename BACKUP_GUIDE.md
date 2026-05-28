# DevFlow 数据备份与恢复指南

## ⚠️ 重要警告

**永远不要使用以下命令，除非明确要清空所有数据：**
```bash
docker-compose down -v  # ❌ 会删除所有数据！
```

## ✅ 正确的停止和启动命令

### 停止服务（保留数据）
```bash
docker-compose stop
# 或
docker-compose down  # 不加 -v 参数
```

### 启动服务
```bash
docker-compose up -d
```

## 💾 数据备份方案

### 1. PostgreSQL数据库备份
```bash
# 备份数据库
docker exec devflow-postgres pg_dump -U devflow_user devflow_db > backup_$(date +%Y%m%d).sql

# 恢复数据库
docker exec -i devflow-postgres psql -U devflow_user devflow_db < backup_20260525.sql
```

### 2. 所有Volume备份
```bash
# 备份所有devflow数据卷
docker run --rm -v devflow_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data
docker run --rm -v devflow_redis_data:/data -v $(pwd):/backup alpine tar czf /backup/redis_backup.tar.gz /data
docker run --rm -v devflow_gitea_data:/data -v $(pwd):/backup alpine tar czf /backup/gitea_backup.tar.gz /data
```

### 3. 完整快照备份
```bash
# 创建所有容器的快照
docker commit devflow-postgres devflow-postgres-backup:$(date +%Y%m%d)
docker commit devflow-backend devflow-backend-backup:$(date +%Y%m%d)
```

## 🔄 数据恢复方案

### 恢复Volume数据
```bash
# 恢复PostgreSQL数据
docker run --rm -v devflow_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_backup.tar.gz -C /
```

## 📋 定期备份脚本

创建 `backup.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/path/to/backups/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# 备份数据库
docker exec devflow-postgres pg_dump -U devflow_user devflow_db > $BACKUP_DIR/database.sql

# 备份所有数据卷
docker run --rm -v devflow_postgres_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/postgres.tar.gz /data
docker run --rm -v devflow_redis_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/redis.tar.gz /data
docker run --rm -v devflow_gitea_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/gitea.tar.gz /data

echo "Backup completed at $BACKUP_DIR"
```

## 🚨 紧急恢复步骤

如果误删了数据，立即执行：

1. **停止所有容器**（不要删除volume）
```bash
docker-compose stop
```

2. **从备份恢复**
```bash
# 恢复数据库
docker exec -i devflow-postgres psql -U devflow_user devflow_db < backup.sql

# 或从volume备份恢复
docker run --rm -v devflow_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_backup.tar.gz -C /
```

3. **重启服务**
```bash
docker-compose up -d
```
