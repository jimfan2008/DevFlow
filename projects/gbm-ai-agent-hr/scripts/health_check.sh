#!/bin/bash
# GBM AI Agent HR - 健康检查脚本
# 使用方式: bash scripts/health_check.sh

set -euo pipefail

echo "=== GBM AI Agent HR Health Check ==="
echo "Timestamp: $(date)"
echo ""

# 检查后端服务
echo "[CHECK] Backend API..."
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "[OK] Backend is healthy"
else
    echo "[FAIL] Backend is NOT responding"
fi

# 检查 MySQL
echo "[CHECK] MySQL..."
if curl -sf "http://localhost:3306" > /dev/null 2>&1 || mysqladmin ping -h localhost -u root -p"${MYSQL_ROOT_PASSWORD:-}" 2>/dev/null | grep -q "alive"; then
    echo "[OK] MySQL is healthy"
else
    echo "[WARN] MySQL status unknown (check Docker)"
fi

# 检查 Redis
echo "[CHECK] Redis..."
if redis-cli -a "${REDIS_PASSWORD:-}" ping 2>/dev/null | grep -q PONG; then
    echo "[OK] Redis is healthy"
else
    echo "[WARN] Redis status unknown (check Docker)"
fi

# 检查 Kafka
echo "[CHECK] Kafka..."
if docker ps --format '{{.Names}}' | grep -q gbm-hr-kafka; then
    echo "[OK] Kafka container is running"
else
    echo "[FAIL] Kafka container NOT running"
fi

# 检查 MinIO
echo "[CHECK] MinIO..."
if curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1; then
    echo "[OK] MinIO is healthy"
else
    echo "[WARN] MinIO status unknown (check Docker)"
fi

# 检查 Celery Worker
echo "[CHECK] Celery Worker..."
if docker ps --format '{{.Names}}' | grep -q gbm-hr-celery-worker; then
    echo "[OK] Celery Worker is running"
else
    echo "[FAIL] Celery Worker NOT running"
fi

# 检查 Docker 容器状态
echo ""
echo "=== Docker Container Status ==="
docker ps --filter "name=gbm-hr" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "[WARN] Docker not accessible"

echo ""
echo "=== Health Check Completed ==="
