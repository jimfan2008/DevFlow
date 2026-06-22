#!/bin/bash
# ============================================
# GBM AI Agent HR - Database Setup Script
# ============================================
# Usage: bash scripts/setup_db.sh [env_file]
# ============================================

set -e

# Load environment variables
ENV_FILE="${1:-.env}"
if [ -f "$ENV_FILE" ]; then
    echo "[INFO] Loading environment from $ENV_FILE"
    set -a
    source "$ENV_FILE"
    set +a
else
    echo "[WARN] $ENV_FILE not found, using defaults"
fi

# Default values
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-hr_admin}"
DB_PASSWORD="${DB_PASSWORD:-gbm_hr_dev_password}"
DB_NAME="${DB_NAME:-gbm_hr_db}"

echo "============================================"
echo "  GBM AI Agent HR - Database Setup"
echo "============================================"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  User: $DB_USER"
echo "  Name: $DB_NAME"
echo "============================================"

# Check MySQL client
if ! command -v mysql &> /dev/null; then
    echo "[ERROR] mysql client not found. Please install MySQL client tools."
    echo "  Ubuntu/Debian: sudo apt install mysql-client"
    echo "  macOS: brew install mysql-client"
    exit 1
fi

# Test connection
echo "[INFO] Testing MySQL connection..."
if ! mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" -e "SELECT 1" &> /dev/null; then
    echo "[ERROR] Cannot connect to MySQL. Check credentials and ensure MySQL is running."
    echo "  Try: docker-compose up -d mysql"
    exit 1
fi
echo "[OK] MySQL connection successful"

# Create schemas
echo "[INFO] Creating schemas..."
mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" -e "
CREATE SCHEMA IF NOT EXISTS \`hr_user\` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE SCHEMA IF NOT EXISTS \`hr_recruit\` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE SCHEMA IF NOT EXISTS \`hr_payroll\` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE SCHEMA IF NOT EXISTS \`hr_auto\` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
"
echo "[OK] Schemas created: hr_user, hr_recruit, hr_payroll, hr_auto"

# Run init SQL
echo "[INFO] Running database initialization script..."
mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" < database/init.sql
echo "[OK] Database initialization complete"

# Run seed data
if [ -f "database/seed.sql" ]; then
    echo "[INFO] Running seed data..."
    mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASSWORD" < database/seed.sql
    echo "[OK] Seed data loaded"
else
    echo "[INFO] No seed.sql found, skipping"
fi

# Run Alembic migrations
echo "[INFO] Running Alembic migrations..."
if command -v alembic &> /dev/null; then
    export DATABASE_URL="mysql+pymysql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
    alembic upgrade head
    echo "[OK] Alembic migrations applied"
else
    echo "[WARN] Alembic not found. Install with: pip install alembic"
fi

# Create MinIO bucket
echo "[INFO] Creating MinIO bucket..."
MINIO_HOST="${MINIO_ENDPOINT:-localhost:9000}"
MINIO_ACCESS="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET="${MINIO_SECRET_KEY:-minioadmin}"

if command -v mc &> /dev/null; then
    mc alias set gbm-hr-storage "https://${MINIO_HOST}" "${MINIO_ACCESS}" "${MINIO_SECRET}" --api S3v4 2>/dev/null || true
    mc mb gbm-hr-storage/hr-documents 2>/dev/null || true
    mc mb gbm-hr-storage/hr-resumes 2>/dev/null || true
    mc mb gbm-hr-storage/hr-certificates 2>/dev/null || true
    mc mb gbm-hr-storage/hr-training 2>/dev/null || true
    echo "[OK] MinIO buckets created"
else
    echo "[WARN] MinIO client (mc) not found. Create buckets manually:"
    echo "  Bucket: hr-documents, hr-resumes, hr-certificates, hr-training"
fi

# Create Kafka topics
echo "[INFO] Creating Kafka topics..."
KAFKA_HOST="${KAFKA_BOOTSTRAP:-localhost:9092}"
if command -v kafka-topics.sh &> /dev/null; then
    TOPICS=(
        "recruitment.resume.inbound"
        "recruitment.interview.created"
        "payroll.monthly.started"
        "payroll.monthly.completed"
        "attendance.daily.sync"
        "training.enrollment.created"
        "external.rpa.task.created"
        "external.rpa.task.completed"
        "agent.orchestration.command"
        "agent.orchestration.result"
    )
    for topic in "${TOPICS[@]}"; do
        kafka-topics.sh --create --if-not-exists \
            --bootstrap-server "$KAFKA_HOST" \
            --partitions 3 \
            --replication-factor 1 \
            --config retention.ms=604800000 \
            --topic "$topic" 2>/dev/null || echo "[WARN] Failed to create topic: $topic"
    done
    echo "[OK] Kafka topics created"
else
    echo "[WARN] kafka-topics.sh not found. Create topics manually or use docker-compose."
fi

echo ""
echo "============================================"
echo "  Database Setup Complete!"
echo "============================================"
echo "  Next steps:"
echo "  1. Start application: docker-compose up -d app worker"
echo "  2. Check health: curl http://localhost:8000/health"
echo "  3. View docs: http://localhost:8000/docs"
echo "============================================"
