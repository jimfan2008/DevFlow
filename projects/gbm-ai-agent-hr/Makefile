# GBM AI Agent HR - Makefile

.PHONY: help infra-up infra-down db-init backend-build backend-test frontend-install frontend-build all-up all-down clean

help:                 ## Show help
    @grep -E '^[a-zA-Z_-]+:.*##.*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

infra-up:             ## Start infrastructure services
    docker compose up -d mysql redis zookeeper kafka1 kafka2 kafka3 minio milvus elasticsearch keycloak zeebe operate tasklist prometheus grafana jaeger

infra-down:           ## Stop infrastructure services
    docker compose down

infra-logs:           ## View infrastructure logs
    docker compose logs -f mysql redis kafka1

db-init:              ## Initialize database schemas
    @echo "Database init scripts are in infra/docker/mysql/init/"
    @echo "Run: docker exec gbm-hr-mysql mysql -uroot -p<password> < infra/docker/mysql/init/01-create-schemas.sql"

backend-build:        ## Build backend
    cd backend && mvn clean install -DskipTests

backend-test:         ## Run backend tests
    cd backend && mvn test

frontend-install:     ## Install frontend dependencies
    cd frontend/web && npm install
    cd frontend/mobile && npm install

frontend-build:       ## Build frontend
    cd frontend/web && npm run build
    cd frontend/mobile && npm run build

all-up:               ## Start all services
    docker compose up -d

all-down:             ## Stop all services
    docker compose down

clean:                ## Clean everything
    docker compose down -v
    cd backend && mvn clean
    rm -rf frontend/web/node_modules frontend/web/dist
    rm -rf frontend/mobile/node_modules frontend/mobile/dist
