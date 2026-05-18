.PHONY: help dev test lint format clean docker-build docker-up docker-down db-reset

# Default target
help:
	@echo "DevFlow Development Commands:"
	@echo ""
	@echo "  make dev          - Start development server"
	@echo "  make test         - Run tests with coverage"
	@echo "  make lint         - Run Ruff linter"
	@echo "  make format       - Format code with Ruff"
	@echo "  make check        - Run lint and format checks"
	@echo "  make docker-build - Build Docker images"
	@echo "  make docker-up    - Start Docker containers"
	@echo "  make docker-down  - Stop Docker containers"
	@echo "  make clean        - Clean up build artifacts"

# Development server
dev:
	@echo "Starting development server..."
	@uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run tests
test:
	@echo "Running tests..."
	@pytest -v --cov=app --cov-report=term-missing

# Run linter
lint:
	@echo "Running linter..."
	@ruff check .

# Format code
format:
	@echo "Formatting code..."
	@ruff format .

# Run all checks
check: lint format
	@echo "All checks passed!"

# Docker commands
docker-build:
	@echo "Building Docker images..."
	@docker-compose build --no-cache

docker-up:
	@echo "Starting Docker containers..."
	@docker-compose up -d

docker-down:
	@echo "Stopping Docker containers..."
	@docker-compose down

docker-logs:
	@docker-compose logs -f

# Database management
db-reset:
	@echo "Resetting database..."
	@docker-compose exec postgres psql -U devflow_user -d devflow_db -c "DROP SCHEMA public CASCADE;"
	@docker-compose exec postgres psql -U devflow_user -d devflow_db -c "CREATE SCHEMA public;"

clean:
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name "*.pytest_cache" -exec rm -rf {} +
	@find . -type d -name ".mypy_cache" -exec rm -rf {} +
	@find . -type d -name ".ruff_cache" -exec rm -rf {} +
	@find . -type f -name "*.coverage" -exec rm -f {} +
	@rm -rf htmlcov/ .tox/ .pytest_cache/
