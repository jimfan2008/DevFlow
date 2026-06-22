#!/bin/bash
# ============================================
# GBM AI Agent HR - Development Environment Startup Script
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "============================================"
echo "GBM AI Agent HR - Development Environment"
echo "============================================"
echo ""

# Check Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check docker-compose
if ! docker compose version >/dev/null 2>&1; then
    echo "ERROR: Docker Compose is not installed. Please install it and try again."
    exit 1
fi

# Load environment variables
if [ -f "$PROJECT_DIR/.env" ]; then
    echo "Loading environment from .env file..."
    set -a
    source "$PROJECT_DIR/.env"
    set +a
else
    echo "WARNING: .env file not found. Using default values from .env.example"
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
        echo "Created .env file from .env.example. Please update with your credentials."
    fi
fi

# Start infrastructure services
echo ""
echo "Starting infrastructure services..."
docker compose up -d mysql redis minio zookeeper kafka-1 kafka-2 kafka-3

# Wait for MySQL to be ready
echo "Waiting for MySQL to be ready..."
until docker compose exec mysql mysqladmin ping -h localhost --silent; do
    echo "MySQL is unavailable - sleeping"
    sleep 5
done
echo "MySQL is ready!"

# Initialize database schemas
echo "Initializing database schemas..."
docker compose exec mysql mysql -u root -p"${MYSQL_ROOT_PASSWORD:-root_password}" < "$PROJECT_DIR/database/init.sql"

# Start remaining services
echo ""
echo "Starting remaining services..."
docker compose up -d keycloak camunda

# Wait for Keycloak to be ready
echo "Waiting for Keycloak to be ready..."
until curl -s http://localhost:8180/realms/master >/dev/null 2>&1; do
    echo "Keycloak is unavailable - sleeping"
    sleep 5
done
echo "Keycloak is ready!"

# Create GBM-HR realm in Keycloak (if not exists)
echo "Setting up Keycloak realm..."
# This step can be automated with a Keycloak initialization script

# Start domain services and sub-services
echo ""
echo "Starting domain services and sub-services..."
docker compose up -d user-domain recruit-domain payroll-domain auto-domain
docker compose up -d rpa-service ocr-service face-service

# Start frontend
echo "Starting frontend..."
docker compose up -d frontend nginx

# Start monitoring
echo "Starting monitoring..."
docker compose up -d prometheus grafana

echo ""
echo "============================================"
echo "Development environment started successfully!"
echo "============================================"
echo ""
echo "Service URLs:"
echo "  Frontend:        http://localhost:3000"
echo "  Nginx Gateway:   http://localhost:80"
echo "  User Domain:     http://localhost:8081"
echo "  Recruit Domain:  http://localhost:8082"
echo "  Payroll Domain:  http://localhost:8083"
echo "  Auto Domain:     http://localhost:8084"
echo "  RPA Service:     http://localhost:8090"
echo "  OCR Service:     http://localhost:8091"
echo "  Face Service:    http://localhost:8092"
echo "  Keycloak:        http://localhost:8180"
echo "  Prometheus:      http://localhost:9090"
echo "  Grafana:         http://localhost:3001 (admin/admin)"
echo "  MinIO Console:   http://localhost:9001"
echo ""
echo "To stop: docker compose down"
echo "To view logs: docker compose logs -f"
echo ""
