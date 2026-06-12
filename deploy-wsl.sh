#!/usr/bin/env bash
# =============================================================================
# DevFlow v4.0 WSL 服务管理脚本 (在 WSL 内部执行)
# =============================================================================
# 用法:
#   bash deploy-wsl.sh start         启动所有服务
#   bash deploy-wsl.sh stop          停止所有服务
#   bash deploy-wsl.sh restart       重启所有服务
#   bash deploy-wsl.sh status        检查服务状态
#   bash deploy-wsl.sh logs [svc]    查看日志 (backend|frontend|all)
#   bash deploy-wsl.sh health        健康检查
#   bash deploy-wsl.sh restart-backend  仅重启后端
#   bash deploy-wsl.sh restart-frontend 仅重启前端
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." 2>/dev/null && pwd || echo "$SCRIPT_DIR")"
PID_DIR="/tmp"
BACKEND_PID_FILE="$PID_DIR/devflow-backend.pid"
FRONTEND_PID_FILE="$PID_DIR/devflow-frontend.pid"
BACKEND_LOG="$PID_DIR/devflow-backend.log"
FRONTEND_LOG="$PID_DIR/devflow-frontend.log"

# 颜色
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_err()   { echo -e "${RED}[ERR]${NC}   $*"; }

# 获取服务 PID
get_pid() {
    local pid_file="$1"
    if [ -f "$pid_file" ]; then
        local pid
        pid=$(cat "$pid_file" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo "$pid"
            return 0
        fi
    fi
    return 1
}

# 通过进程名查找
find_process() {
    local pattern="$1"
    pgrep -f "$pattern" 2>/dev/null | head -1
}

# 停止服务
stop_service() {
    local name="$1"
    local pid_file="$2"
    local pattern="$3"
    local pid

    pid=$(get_pid "$pid_file" 2>/dev/null || true)
    if [ -z "$pid" ]; then
        pid=$(find_process "$pattern")
    fi

    if [ -n "$pid" ]; then
        log_info "停止 $name (PID: $pid)..."
        kill "$pid" 2>/dev/null || true
        sleep 1
        if kill -0 "$pid" 2>/dev/null; then
            log_warn "$name 未响应，强制终止..."
            kill -9 "$pid" 2>/dev/null || true
        fi
        rm -f "$pid_file"
        log_ok "$name 已停止"
    else
        log_info "$name 未运行"
    fi
}

# 检查服务状态
check_service() {
    local name="$1"
    local pid_file="$2"
    local pattern="$3"
    local pid

    pid=$(get_pid "$pid_file" 2>/dev/null || true)
    if [ -z "$pid" ]; then
        pid=$(find_process "$pattern")
    fi

    if [ -n "$pid" ]; then
        echo -e "  ${GREEN}●${NC} $name (PID: $pid)"
        return 0
    else
        echo -e "  ${RED}○${NC} $name (未运行)"
        return 1
    fi
}

# 启动后端
start_backend() {
    log_info "启动 FastAPI 后端..."
    cd "$PROJECT_DIR/backend"

    if [ ! -d ".venv" ]; then
        log_err "虚拟环境不存在，请先运行部署脚本"
        return 1
    fi

    source .venv/bin/activate

    nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > "$BACKEND_LOG" 2>&1 &
    echo $! > "$BACKEND_PID_FILE"
    log_ok "后端已启动 (PID: $(cat "$BACKEND_PID_FILE"))"

    # 等待就绪
    for i in $(seq 1 30); do
        if curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health 2>/dev/null | grep -q 200; then
            log_ok "后端健康检查通过"
            return 0
        fi
        sleep 1
    done
    log_warn "后端可能仍在启动中"
}

# 启动前端
start_frontend() {
    log_info "启动 Vite 前端..."
    cd "$PROJECT_DIR/frontend"

    if [ ! -d "node_modules" ]; then
        log_err "node_modules 不存在，请先运行 npm install"
        return 1
    fi

    nohup npm run dev -- --host 0.0.0.0 > "$FRONTEND_LOG" 2>&1 &
    echo $! > "$FRONTEND_PID_FILE"
    log_ok "前端已启动 (PID: $(cat "$FRONTEND_PID_FILE"))"
}

# 启动 Docker 基础设施
start_docker() {
    log_info "检查 Docker 基础设施..."
    cd "$PROJECT_DIR"

    if docker compose -f docker-compose.dev.yml ps --format '{{.Names}}' 2>/dev/null | grep -q 'devflow-postgres'; then
        log_info "Docker 服务已在运行"
        return 0
    fi

    log_info "启动 Docker 服务..."
    docker compose -f docker-compose.dev.yml up -d postgres redis gitea-db gitea 2>&1 | while read -r line; do
        echo "  $line"
    done
    log_ok "Docker 基础设施已启动"
    sleep 3
}

# 查看日志
show_logs() {
    local target="${1:-all}"
    case "$target" in
        backend)
            echo -e "${CYAN}=== 后端日志 ===${NC}"
            tail -f "$BACKEND_LOG"
            ;;
        frontend)
            echo -e "${CYAN}=== 前端日志 ===${NC}"
            tail -f "$FRONTEND_LOG"
            ;;
        all|*)
            echo -e "${CYAN}=== 后端日志 ===${NC}"
            tail -20 "$BACKEND_LOG" 2>/dev/null || echo "无日志"
            echo ""
            echo -e "${CYAN}=== 前端日志 ===${NC}"
            tail -20 "$FRONTEND_LOG" 2>/dev/null || echo "无日志"
            ;;
    esac
}

# 健康检查
do_health_check() {
    echo "============================================"
    echo "  DevFlow v4.0 健康检查"
    echo "  $(date '+%Y-%m-%d %H:%M:%S')"
    echo "============================================"

    # 后端
    if curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health 2>/dev/null | grep -q 200; then
        local health_json
        health_json=$(curl -s http://localhost:8000/health 2>/dev/null)
        echo -e "${GREEN}✅ 后端 API: 正常${NC}"
        echo "   $health_json"
    else
        echo -e "${RED}❌ 后端 API: 不可达${NC}"
    fi

    # 前端
    if curl -s -o /dev/null -w '%{http_code}' http://localhost:5173 2>/dev/null | grep -q '200\|302'; then
        echo -e "${GREEN}✅ 前端: 正常${NC}"
    else
        echo -e "${YELLOW}⚠️  前端: 不可达 (可能未启动)${NC}"
    fi

    # API 文档
    if curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/docs 2>/dev/null | grep -q 200; then
        echo -e "${GREEN}✅ API 文档: 可访问${NC}"
    else
        echo -e "${YELLOW}⚠️  API 文档: 不可达${NC}"
    fi

    # Docker
    if command -v docker &>/dev/null; then
        local dc_count
        dc_count=$(cd "$PROJECT_DIR" && docker compose -f docker-compose.dev.yml ps -q 2>/dev/null | wc -l || echo 0)
        echo -e "${GREEN}✅ Docker: ${dc_count} 个容器运行中${NC}"
    fi

    # 磁盘
    local disk
    disk=$(df -h / | tail -1 | awk '{print $5 " used (" $4 " free)"}')
    echo "   📀 磁盘: $disk"

    # 内存
    local mem
    mem=$(free -h | awk '/^Mem:/ {print $3 "/" $2}')
    echo "   🧠 内存: $mem"

    echo "============================================"
}

# 显示状态
show_status() {
    echo "============================================"
    echo "  DevFlow v4.0 服务状态"
    echo "  $(date '+%Y-%m-%d %H:%M:%S')"
    echo "============================================"
    check_service "FastAPI 后端"  "$BACKEND_PID_FILE"  "uvicorn app.main"
    check_service "Vite 前端"    "$FRONTEND_PID_FILE" "vite"
    if command -v docker &>/dev/null; then
        local containers
        containers=$(cd "$PROJECT_DIR" && docker compose -f docker-compose.dev.yml ps --format 'table {{.Names}}\t{{.Status}}' 2>/dev/null || echo "")
        if [ -n "$containers" ]; then
            echo ""
            echo "  Docker 容器:"
            echo "$containers" | while read -r line; do echo "    $line"; done
        fi
    fi
    echo ""
    echo "  后端日志: $BACKEND_LOG"
    echo "  前端日志: $FRONTEND_LOG"
    echo "============================================"
}

# ── 主命令分发 ─────────────────────────────────────────────────────
case "${1:-status}" in
    start)
        echo "============================================"
        echo "  启动 DevFlow v4.0 所有服务"
        echo "============================================"
        start_docker 2>/dev/null || true
        start_backend
        start_frontend
        echo ""
        show_status
        ;;

    stop)
        echo "============================================"
        echo "  停止 DevFlow v4.0 所有服务"
        echo "============================================"
        stop_service "后端" "$BACKEND_PID_FILE" "uvicorn app.main"
        stop_service "前端" "$FRONTEND_PID_FILE" "vite"
        log_ok "所有服务已停止"
        ;;

    restart)
        bash "$0" stop
        sleep 1
        bash "$0" start
        ;;

    restart-backend)
        stop_service "后端" "$BACKEND_PID_FILE" "uvicorn app.main"
        sleep 1
        start_backend
        ;;

    restart-frontend)
        stop_service "前端" "$FRONTEND_PID_FILE" "vite"
        sleep 1
        start_frontend
        ;;

    status)
        show_status
        ;;

    logs)
        show_logs "${2:-all}"
        ;;

    health)
        do_health_check
        ;;

    *)
        echo "DevFlow v4.0 WSL 服务管理"
        echo ""
        echo "用法: $0 {start|stop|restart|status|logs|health|restart-backend|restart-frontend}"
        echo ""
        echo "  start             启动所有服务"
        echo "  stop              停止所有服务"
        echo "  restart           重启所有服务"
        echo "  status            查看服务状态"
        echo "  logs [svc]        查看日志 (backend|frontend|all)"
        echo "  health            健康检查"
        echo "  restart-backend   仅重启后端"
        echo "  restart-frontend  仅重启前端"
        exit 1
        ;;
esac