#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# DevFlow 一键启动脚本 v4.0
# 启动: 后端 + 前端 + 9个 Hermes Agent + 数据库初始化
# =============================================================================

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 从配置文件读取端口
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

export BACKEND_PORT=${BACKEND_PORT:-9000}
export FRONTEND_PORT=${FRONTEND_PORT:-6000}

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
err()   { echo -e "${RED}[ERR]${NC}   $1"; }

cleanup() {
    echo ""
    info "Shutting down DevFlow..."
    # 先 SIGTERM，1秒后 SIGKILL 残留
    for pid in "${BACKEND_PID:-}" "${FRONTEND_PID:-}" "${HERMES_PIDS[@]}"; do
        [ -n "$pid" ] && kill "$pid" 2>/dev/null || true
    done
    sleep 1
    for pid in "${BACKEND_PID:-}" "${FRONTEND_PID:-}" "${HERMES_PIDS[@]}"; do
        [ -n "$pid" ] && kill -9 "$pid" 2>/dev/null || true
    done
    ok "All services stopped"
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

cleanup_ports() {
    local ports=("$BACKEND_PORT" "$FRONTEND_PORT")
    for port in "${ports[@]}"; do
        local pids
        pids=$(lsof -ti :"$port" 2>/dev/null) || true
        if [ -n "$pids" ]; then
            warn "Port $port 被以下进程占用，正在清理: $(echo "$pids" | tr '\n' ' ')"
            echo "$pids" | xargs kill -9 2>/dev/null || true
            sleep 1
        fi
    done
}

HERMES_PIDS=()

check_deps() {
    for cmd in python3 node npm; do
        command -v "$cmd" &>/dev/null || { err "$cmd not found"; return 1; }
    done
    PYTHONPATH="$PROJECT_DIR/backend" python3 -c "import fastapi" 2>/dev/null || {
        warn "Installing Python deps..."
        pip install -q -r "$PROJECT_DIR/requirements.txt" 2>/dev/null || \
        pip install -q fastapi uvicorn sqlalchemy pydantic-settings httpx aiosqlite slowapi
    }
    if [ ! -d "$PROJECT_DIR/frontend/node_modules" ]; then
        info "Installing frontend deps..."
        npm --prefix "$PROJECT_DIR/frontend" install
    fi
    command -v hermes &>/dev/null || warn "hermes CLI not in PATH"
}

start_backend() {
    info "Starting backend on port $BACKEND_PORT..."
    cd "$PROJECT_DIR"
    PYTHONPATH="$PROJECT_DIR/backend" \
    HERMES_PROFILES_PATH="${HERMES_PROFILES_PATH:-$HOME/.hermes}" \
    DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./devflow.db}" \
    uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --log-level info &
    BACKEND_PID=$!
    for i in $(seq 1 30); do
        if curl -s "http://127.0.0.1:$BACKEND_PORT/health" >/dev/null 2>&1; then
            ok "Backend: http://localhost:$BACKEND_PORT"
            return 0
        fi
        sleep 1
    done
    err "Backend failed to start"; return 1
}

start_frontend() {
    info "Starting frontend on port $FRONTEND_PORT..."
    npm --prefix "$PROJECT_DIR/frontend" run dev -- --port "$FRONTEND_PORT" --host &
    FRONTEND_PID=$!
    sleep 4
    ok "Frontend: http://localhost:$FRONTEND_PORT"
}

# ── 启动所有 Hermes Agent（9 大角色） ─────────────────
start_hermes_agents() {
    info "Starting 9 Hermes Agent roles..."
    HERMES_BIN="${HERMES_BIN:-$(command -v hermes)}"
    if [ -z "$HERMES_BIN" ]; then
        warn "hermes CLI not found, skipping agent startup"
        return
    fi

    # 默认 profile = haimei，其余有独立 profile
    PROFILES=("" "houda" "houfa" "houfu" "hougui" "houhua" "hourong" "houwang" "houxing")

    for p in "${PROFILES[@]}"; do
        local name="${p:-default}"
        local pid_file="/tmp/hermes_${name}.pid"

        # 检查是否已在运行
        if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
            ok "  $name already running (PID $(cat "$pid_file"))"
            HERMES_PIDS+=("$(cat "$pid_file")")
            continue
        fi

        local log_file="/tmp/hermes_${name}.log"
        if [ -z "$p" ]; then
            "$HERMES_BIN" gateway run --accept-hooks &>"$log_file" &
        else
            "$HERMES_BIN" gateway run --profile "$p" --accept-hooks &>"$log_file" &
        fi
        local pid=$!
        echo "$pid" > "$pid_file"
        HERMES_PIDS+=("$pid")
        ok "  ${p:-default} started (PID $pid)"
    done

    # 等几秒确保所有 agent 启动
    sleep 3
    echo ""
    "$HERMES_BIN" gateway list 2>&1 | while IFS= read -r line; do
        echo -e "  ${CYAN}${line}${NC}"
    done
}

# ── 将 Hermes 网关状态同步到 DevFlow DB ────────────────
sync_agent_status() {
    info "Syncing agent status to DevFlow..."
    local status_output
    status_output=$("$HERMES_BIN" gateway list 2>/dev/null) || return

    cd "$PROJECT_DIR"
    PYTHONPATH="$PROJECT_DIR/backend" python3 -c "
import os, subprocess, json, sys
os.environ['HERMES_PROFILES_PATH'] = os.path.expanduser('${HERMES_PROFILES_PATH:-~/.hermes}')
from app.database import SessionLocal, sync_engine, Base
from app.models.agent import Agent

Base.metadata.create_all(bind=sync_engine)
db = SessionLocal()
try:
    # 运行 hermes gateway list 获取状态
    result = subprocess.run(['hermes', 'gateway', 'list'], capture_output=True, text=True, timeout=10)
    lines = result.stdout.strip().split('\n')
    online_profiles = set()
    for line in lines:
        if '✓' in line:
            parts = line.split()
            for part in parts:
                if part in ('default',) or (part.startswith('hou') or part.startswith('hai')):
                    profile = 'default' if part == 'default' else part
                    online_profiles.add(profile)
                    break

    # 名字映射
    name_map = {
        'default': 'haimei', 'houda': 'houda', 'houfa': 'houfa',
        'houfu': 'houfu', 'hougui': 'hougui', 'houhua': 'houhua',
        'hourong': 'hourong', 'houwang': 'houwang', 'houxing': 'houxing',
    }

    count = 0
    for profile, name in name_map.items():
        agent = db.query(Agent).filter(Agent.name == name, Agent.is_named_role == True).first()
        if agent:
            was = agent.status
            agent.status = 'online' if profile in online_profiles else 'offline'
            if was != agent.status:
                print(f'  {name}: {was} -> {agent.status}')
                count += 1
    db.commit()
    print(f'Synced {count} agents')
except Exception as e:
    print(f'Sync error: {e}', file=sys.stderr)
finally:
    db.close()
" 2>&1 | while IFS= read -r line; do echo -e "  ${CYAN}${line}${NC}"; done
}

print_info() {
    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}  DevFlow v4.0 已启动!${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
    echo -e "  ${CYAN}Frontend:${NC}   http://localhost:${FRONTEND_PORT}"
    echo -e "  ${CYAN}Backend:${NC}    http://localhost:${BACKEND_PORT}"
    echo -e "  ${CYAN}API Docs:${NC}   http://localhost:${BACKEND_PORT}/docs"
    echo -e "  ${CYAN}Hermes:${NC}     http://localhost:8642/health"
    echo ""
    echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop all services"
    echo ""
}

main() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║        DevFlow 一键启动脚本 v4.0        ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
    echo ""

    check_deps
    cleanup_ports
    start_backend
    start_hermes_agents
    sync_agent_status
    start_frontend
    print_info

    wait
}

main "$@"
