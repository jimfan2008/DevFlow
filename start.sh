#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-5173}
MODE=${1:-dev}  # dev, docker, docker-dev

cleanup() {
  echo ""
  echo "Shutting down..."
  [ -n "${BACKEND_PID:-}" ] && kill "$BACKEND_PID" 2>/dev/null
  [ -n "${FRONTEND_PID:-}" ] && kill "$FRONTEND_PID" 2>/dev/null
  exit 0
}
trap cleanup SIGINT SIGTERM

start_backend() {
  echo "[backend] Starting FastAPI..."

  if [ ! -f "$PROJECT_DIR/.venv/bin/activate" ]; then
    echo "[backend] Creating virtual environment..."
    rm -rf "$PROJECT_DIR/.venv"
    python3 -m venv "$PROJECT_DIR/.venv"
  fi

  # shellcheck disable=SC1091
  source "$PROJECT_DIR/.venv/bin/activate"

  if ! pip install -q -r "$PROJECT_DIR/requirements.txt" 2>/dev/null; then
    pip install -q fastapi uvicorn python-jose passlib asyncpg sqlalchemy pydantic-settings python-dotenv httpx tenacity
  fi

  uvicorn main:app --reload --host 0.0.0.0 --port "$BACKEND_PORT" &
  BACKEND_PID=$!
  echo "[backend] Running on http://localhost:$BACKEND_PORT"
}

start_frontend() {
  echo "[frontend] Starting Vite dev server..."

  if [ ! -d "$PROJECT_DIR/frontend/node_modules" ]; then
    echo "[frontend] Installing npm dependencies..."
    npm --prefix "$PROJECT_DIR/frontend" install
  fi

  npm --prefix "$PROJECT_DIR/frontend" run dev -- --port "$FRONTEND_PORT" &
  FRONTEND_PID=$!
  echo "[frontend] Running on http://localhost:$FRONTEND_PORT"
}

case "$MODE" in
  docker)
    echo "=== DevFlow (Docker Production) ==="
    cd "$PROJECT_DIR"
    docker compose up -d
    echo "Backend: http://localhost:8001"
    docker compose logs -f
    ;;
  docker-dev)
    echo "=== DevFlow (Docker Development) ==="
    cd "$PROJECT_DIR"
    docker compose -f docker-compose.dev.yml up -d
    echo "Backend: http://localhost:8000"
    echo "Frontend: http://localhost:80"
    docker compose -f docker-compose.dev.yml logs -f
    ;;
  dev)
    echo "=== DevFlow (Local Development) ==="
    start_backend
    start_frontend
    echo ""
    echo "Backend:  http://localhost:$BACKEND_PORT"
    echo "Frontend: http://localhost:$FRONTEND_PORT"
    echo "Docs:     http://localhost:$BACKEND_PORT/docs"
    echo "Press Ctrl+C to stop"
    wait
    ;;
  *)
    echo "Usage: $0 [dev|docker|docker-dev]"
    echo "  dev        Local development (default)"
    echo "  docker     Docker Compose production"
    echo "  docker-dev Docker Compose development"
    exit 1
    ;;
esac
