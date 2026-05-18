#!/bin/bash
set -e

echo "=== DevFlow Application Startup ==="
echo "Timestamp: $(date)"

MAX_RETRIES=30
RETRY_DELAY=2
RETRY_COUNT=0

if command -v pg_isready &> /dev/null; then
    echo "Waiting for database connection..."
    DB_HOST="${POSTGRES_HOST:-postgres}"
    DB_PORT="${POSTGRES_PORT:-5432}"
    DB_USER="${POSTGRES_USER:-devflow_user}"
    DB_NAME="${POSTGRES_DB:-devflow_db}"

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" 2>/dev/null; then
            echo "Database is ready!"
            break
        fi
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
            echo "WARNING: Database readiness check failed after $MAX_RETRIES attempts, continuing anyway..."
            break
        fi
        echo "Waiting for database... (attempt $RETRY_COUNT/$MAX_RETRIES)"
        sleep $RETRY_DELAY
    done
else
    echo "pg_isready not available, skipping database readiness check"
fi

echo "Checking environment configuration..."
if [ -z "${JWT_SECRET:-}" ]; then
    echo "WARNING: JWT_SECRET is not set, using default (not secure for production)"
    export JWT_SECRET="dev-jwt-secret-change-in-production"
fi
if [ -z "${DATABASE_URL:-}" ]; then
    echo "WARNING: DATABASE_URL is not set, using SQLite fallback"
    export DATABASE_URL="sqlite:///./devflow.db"
fi
echo "Configuration check passed!"

if [ -d "backend/alembic" ] && [ -n "${RUN_MIGRATIONS:-}" ]; then
    echo "Running database migrations..."
    cd backend && alembic upgrade head && cd ..
fi

echo "Starting FastAPI application..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 ${WORKERS:+--workers $WORKERS}
