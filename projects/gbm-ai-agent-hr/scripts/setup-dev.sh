#!/bin/bash
# GBM AI Agent HR - Development Environment Setup Script
# Run: ./scripts/setup-dev.sh

set -e

echo "=========================================="
echo "GBM AI Agent HR - Development Environment"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
check_prerequisites() {
    echo -e "\n${YELLOW}Checking prerequisites...${NC}"

    local missing=0

    # Check Git
    if command -v git &> /dev/null; then
        echo -e "${GREEN}[OK]${NC} Git: $(git --version)"
    else
        echo -e "${RED}[MISSING]${NC} Git - Install from https://git-scm.com/"
        missing=1
    fi

    # Check Java
    if command -v java &> /dev/null; then
        echo -e "${GREEN}[OK]${NC} Java: $(java -version 2>&1 | head -1)"
    else
        echo -e "${RED}[MISSING]${NC} Java 17 - Install Eclipse Temurin 17"
        missing=1
    fi

    # Check Maven
    if command -v mvn &> /dev/null; then
        echo -e "${GREEN}[OK]${NC} Maven: $(mvn --version | head -1)"
    else
        echo -e "${RED}[MISSING]${NC} Maven 3.8+ - Install from https://maven.apache.org/"
        missing=1
    fi

    # Check Node.js
    if command -v node &> /dev/null; then
        echo -e "${GREEN}[OK]${NC} Node.js: $(node --version)"
    else
        echo -e "${RED}[MISSING]${NC} Node.js 18 LTS - Install from https://nodejs.org/"
        missing=1
    fi

    # Check Python
    if command -v python3 &> /dev/null; then
        echo -e "${GREEN}[OK]${NC} Python: $(python3 --version)"
    else
        echo -e "${RED}[MISSING]${NC} Python 3.11+ - Install from https://www.python.org/"
        missing=1
    fi

    # Check Docker
    if command -v docker &> /dev/null; then
        echo -e "${GREEN}[OK]${NC} Docker: $(docker --version)"
    else
        echo -e "${RED}[MISSING]${NC} Docker - Install from https://docs.docker.com/get-docker/"
        missing=1
    fi

    # Check Docker Compose
    if docker compose version &> /dev/null; then
        echo -e "${GREEN}[OK]${NC} Docker Compose"
    else
        echo -e "${RED}[MISSING]${NC} Docker Compose"
        missing=1
    fi

    if [ $missing -eq 1 ]; then
        echo -e "\n${RED}Some prerequisites are missing. Please install them and try again.${NC}"
        exit 1
    fi

    echo -e "${GREEN}All prerequisites satisfied!${NC}"
}

# Copy environment file
setup_env() {
    echo -e "\n${YELLOW}Setting up environment...${NC}"

    if [ ! -f .env ]; then
        cp infra/docker/.env.example .env
        echo -e "${GREEN}[OK]${NC} Created .env from .env.example"
        echo -e "${YELLOW}Please update .env with your actual credentials!${NC}"
    else
        echo -e "${YELLOW}[SKIP]${NC} .env already exists"
    fi
}

# Start infrastructure services
start_infra() {
    echo -e "\n${YELLOW}Starting infrastructure services...${NC}"

    # Start infrastructure
    docker compose -f infra/docker/docker-compose.infra.yml up -d

    echo -e "${GREEN}[OK]${NC} Infrastructure services started"
}

# Wait for services to be healthy
wait_for_services() {
    echo -e "\n${YELLOW}Waiting for services to be healthy...${NC}"

    local timeout=180
    local elapsed=0

    while [ $elapsed -lt $timeout ]; do
        local healthy=true

        # Check MySQL
        if docker exec gbm-hr-mysql mysqladmin ping -h localhost &> /dev/null; then
            echo -e "${GREEN}[OK]${NC} MySQL"
        else
            healthy=false
        fi

        # Check Redis
        if docker exec gbm-hr-redis redis-cli ping &> /dev/null; then
            echo -e "${GREEN}[OK]${NC} Redis"
        else
            healthy=false
        fi

        # Check Kafka
        if docker exec gbm-hr-kafka1 kafka-broker-api-versions --bootstrap-server localhost:9092 &> /dev/null; then
            echo -e "${GREEN}[OK]${NC} Kafka"
        else
            healthy=false
        fi

        # Check Elasticsearch
        if curl -s -u elastic:gbm_elastic_2026 http://localhost:9200/_cluster/health &> /dev/null; then
            echo -e "${GREEN}[OK]${NC} Elasticsearch"
        else
            healthy=false
        fi

        if [ $healthy = true ]; then
            echo -e "\n${GREEN}All services are healthy!${NC}"
            return 0
        fi

        echo -e "${YELLOW}Waiting for services... ($elapsed/${timeout}s)${NC}"
        sleep 10
        elapsed=$((elapsed + 10))
    done

    echo -e "${RED}Timeout waiting for services to become healthy.${NC}"
    echo -e "${YELLOW}Check logs with: docker compose -f infra/docker/docker-compose.infra.yml logs${NC}"
    return 1
}

# Initialize database
init_database() {
    echo -e "\n${YELLOW}Database will be initialized on first MySQL startup.${NC}"
    echo -e "${YELLOW}The init scripts in database/init/ will run automatically.${NC}"
}

# Show service URLs
show_urls() {
    echo -e "\n${GREEN}=========================================="
    echo -e "GBM AI Agent HR - Service URLs"
    echo -e "==========================================${NC}"
    echo ""
    echo -e "${YELLOW}Application:${NC}"
    echo "  Frontend (Web):      http://localhost"
    echo "  User Domain:         http://localhost:8081"
    echo "  Recruit Domain:      http://localhost:8082"
    echo "  Payroll Domain:      http://localhost:8083"
    echo "  Auto Domain:         http://localhost:8084"
    echo ""
    echo -e "${YELLOW}Infrastructure:${NC}"
    echo "  MySQL:               localhost:3306"
    echo "  Redis:               localhost:6379"
    echo "  Kafka:               localhost:9092"
    echo "  MinIO API:           http://localhost:9000"
    echo "  MinIO Console:       http://localhost:9001"
    echo "  Elasticsearch:       http://localhost:9200"
    echo "  Milvus:              localhost:19530"
    echo ""
    echo -e "${YELLOW}Authentication:${NC}"
    echo "  Keycloak Admin:      http://localhost:8088/admin"
    echo "  Keycloak Auth:       http://localhost:8088/auth"
    echo ""
    echo -e "${YELLOW}Monitoring:${NC}"
    echo "  Prometheus:          http://localhost:9090"
    echo "  Grafana:             http://localhost:3000"
    echo ""
    echo -e "${YELLOW}Default Credentials:${NC}"
    echo "  MySQL:               gbm_hr_admin / gbm_hr_admin_2026"
    echo "  Keycloak:            admin / gbm_admin_2026"
    echo "  Grafana:             admin / gbm_grafana_2026"
    echo ""
    echo -e "${YELLOW}Useful Commands:${NC}"
    echo "  Start all:           docker compose -f infra/docker/docker-compose.infra.yml -f infra/docker/docker-compose.app.yml up -d"
    echo "  Start infra only:    docker compose -f infra/docker/docker-compose.infra.yml up -d"
    echo "  Stop all:            docker compose -f infra/docker/docker-compose.infra.yml -f infra/docker/docker-compose.app.yml down"
    echo "  View logs:           docker compose logs -f <service-name>"
    echo "  Restart:             docker compose -f infra/docker/docker-compose.infra.yml -f infra/docker/docker-compose.app.yml restart"
}

# Main execution
main() {
    check_prerequisites
    setup_env
    start_infra
    wait_for_services
    init_database
    show_urls

    echo -e "\n${GREEN}Development environment setup complete!${NC}"
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Update .env with your actual credentials"
    echo "2. Start application services: docker compose -f infra/docker/docker-compose.app.yml up -d"
    echo "3. Access the frontend at http://localhost"
}

# Run main
main "$@"
