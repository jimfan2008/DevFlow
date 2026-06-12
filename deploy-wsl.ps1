<#
.SYNOPSIS
    DevFlow v4.0 WSL 自动部署脚本
.DESCRIPTION
    一键将 DevFlow 项目部署到 WSL (Windows Subsystem for Linux) 环境。
    自动处理环境检查、依赖安装、数据库配置、后端/前端启动。
.PARAMETER WslDistro
    WSL 发行版名称，默认 "Ubuntu"
.PARAMETER ProjectPath
    WSL 内的项目路径，默认 "/home/$env:USER/devflow"
.PARAMETER Mode
    部署模式: dev (开发), docker (Docker), docker-dev (Docker开发)
.PARAMETER SkipFrontend
    跳过前端部署
.PARAMETER SkipDocker
    跳过 Docker 基础设施（PostgreSQL/Redis/Gitea），使用 SQLite 模式
.PARAMETER Force
    强制重新部署，覆盖已有配置
.EXAMPLE
    .\deploy-wsl.ps1
    默认：开发模式完整部署
.EXAMPLE
    .\deploy-wsl.ps1 -Mode docker-dev
    Docker 开发模式部署
.EXAMPLE
    .\deploy-wsl.ps1 -SkipDocker -Force
    SQLite 模式，强制重新部署
#>

[CmdletBinding()]
param(
    [string] $WslDistro = "Ubuntu",
    [string] $ProjectPath = "",
    [ValidateSet("dev", "docker", "docker-dev")]
    [string] $Mode = "dev",
    [switch] $SkipFrontend,
    [switch] $SkipDocker,
    [switch] $Force
)

$ErrorActionPreference = "Stop"
$script:StartTime = Get-Date

# ── 颜色输出 ──────────────────────────────────────────────────────
function Write-Step  { param([string]$m) Write-Host "`n━━━ $m ━━━" -ForegroundColor Cyan }
function Write-OK    { param([string]$m) Write-Host "  ✅ $m" -ForegroundColor Green }
function Write-Warn  { param([string]$m) Write-Host "  ⚠️  $m" -ForegroundColor Yellow }
function Write-Err   { param([string]$m) Write-Host "  ❌ $m" -ForegroundColor Red }
function Write-Info  { param([string]$m) Write-Host "  📋 $m" -ForegroundColor Gray }

# ── WSL 命令封装 ───────────────────────────────────────────────────
function Invoke-Wsl {
    param([string]$Command, [switch]$NoProfile)
    $wslCmd = if ($NoProfile) { "wsl -d $WslDistro -- bash --noprofile --norc -c" }
              else { "wsl -d $WslDistro -- bash -c" }
    $escaped = $Command -replace '"', '\"'
    return Invoke-Expression "$wslCmd `"$escaped`""
}

function Test-WslCommand {
    param([string]$Command)
    try {
        $null = Invoke-Wsl -Command $Command -NoProfile
        return $true
    } catch { return $false }
}

# ── Step 1: 预检 ──────────────────────────────────────────────────
Write-Step "Step 1/6: 环境预检"

# 1.1 检查 WSL
Write-Info "检查 WSL 状态..."
try {
    $wslList = wsl --list --verbose 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Err "WSL 未安装或未启用，请先安装 WSL: wsl --install"
        exit 1
    }
    if ($wslList -notmatch $WslDistro) {
        Write-Err "WSL 发行版 '$WslDistro' 未找到"
        Write-Info "可用发行版:"
        wsl --list --quiet | ForEach-Object { Write-Info "  - $_" }
        exit 1
    }
    Write-OK "WSL 发行版 '$WslDistro' 已就绪"
} catch {
    Write-Err "WSL 检查失败: $_"
    exit 1
}

# 1.2 检查 Docker Desktop (如果需要)
if (-not $SkipDocker) {
    Write-Info "检查 Docker..."
    try {
        $dockerOk = Invoke-Wsl -Command "docker info > /dev/null 2>&1 && echo 'OK'" -NoProfile
        if ($dockerOk -match "OK") {
            Write-OK "Docker 可用"
        } else {
            Write-Warn "Docker 不可用，将使用 SQLite 模式"
            $SkipDocker = $true
        }
    } catch {
        Write-Warn "Docker 检测失败，使用 SQLite 模式"
        $SkipDocker = $true
    }
}

# 1.3 检查 Git
Write-Info "检查 Git..."
if (Test-WslCommand -Command "git --version") {
    Write-OK "Git 已安装"
} else {
    Write-Warn "安装 Git..."
    Invoke-Wsl -Command "sudo apt-get update -qq && sudo apt-get install -y -qq git" -NoProfile
    Write-OK "Git 安装完成"
}

# 1.4 确定项目路径
if (-not $ProjectPath) {
    $wslHome = Invoke-Wsl -Command 'echo $HOME' -NoProfile
    $ProjectPath = "$wslHome/devflow"
}
Write-Info "项目路径: $ProjectPath"

# ── Step 2: 克隆/更新项目 ─────────────────────────────────────────
Write-Step "Step 2/6: 项目代码同步"

$repoExists = Test-WslCommand -Command "[ -d '$ProjectPath/.git' ] && echo 'YES' || echo 'NO'"

if ($repoExists -match "YES" -and -not $Force) {
    Write-Info "项目已存在，执行 git pull..."
    Invoke-Wsl -Command @"
cd '$ProjectPath'
git fetch origin main 2>/dev/null
LOCAL=\$(git rev-parse HEAD)
REMOTE=\$(git rev-parse origin/main)
if [ "\$LOCAL" != "\$REMOTE" ]; then
    echo '[UPDATE] 发现新版本，正在更新...'
    git reset --hard origin/main
    echo '[UPDATE] 更新完成'
else
    echo '[OK] 代码已是最新'
fi
"@
    Write-OK "代码同步完成"
} else {
    if ($repoExists -match "YES" -and $Force) {
        Write-Warn "强制模式: 备份并重新克隆..."
        $backupDir = "${ProjectPath}_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        Invoke-Wsl -Command "mv '$ProjectPath' '$backupDir'"
        Write-Info "已备份至 WSL 目录: $backupDir"
    }
    Write-Info "克隆项目..."
    Invoke-Wsl -Command "git clone https://github.com/jimfan2008/DevFlow.git '$ProjectPath'" -NoProfile
    Write-OK "项目克隆完成"
}

# ── Step 3: 环境配置 ──────────────────────────────────────────────
Write-Step "Step 3/6: 环境配置"

# 3.1 创建 .env 文件
$defaultPass = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((Get-Random -Minimum 10000000 -Maximum 99999999).ToString())) + [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((Get-Random -Minimum 10000000 -Maximum 99999999).ToString()))

$envContent = @"
# ================================================================
# DevFlow v4.0 WSL 部署环境配置
# 生成时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
# ================================================================

# 应用配置
APP_NAME=DevFlow
APP_DEBUG=$($Mode -eq 'dev')
APP_HOST=0.0.0.0
APP_PORT=8000

# JWT 认证 (自动生成)
JWT_SECRET=$defaultPass
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=$($Mode -eq 'docker' ? '60' : '30')

# 数据库配置
DATABASE_URL=$(if ($SkipDocker) { 'sqlite+aiosqlite:///./devflow.db' } else { 'postgresql+asyncpg://devflow_user:devflow_password@localhost:5432/devflow_db' })
REDIS_URL=$(if ($SkipDocker) { 'redis://localhost:6379/0' } else { 'redis://localhost:6379/0' })

# 连接池
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30

# Gitea
GITEA_HOST=localhost
GITEA_PORT=3000
GITEA_PROTOCOL=http

# Hermes Agent
HERMES_PROFILES_PATH=~/.hermes
HERMES_GATEWAY_TIMEOUT=360
HERMES_MAX_CONCURRENT=5

# 前端 URL
FRONTEND_URL=http://localhost:80

# 特性开关
ENABLE_REDIS_CACHE=$(if ($SkipDocker) { 'false' } else { 'true' })
ENABLE_METRICS=true
LOG_LEVEL=$(if ($Mode -eq 'dev') { 'DEBUG' } else { 'INFO' })
"@

Invoke-Wsl -Command "cat > '$ProjectPath/backend/.env' << 'ENVEOF'
$envContent
ENVEOF"
Write-OK ".env 配置文件已生成"

# 3.2 设置 WSL 端口代理 (Windows 可访问 WSL 服务)
Write-Info "配置端口转发..."
$wslIp = Invoke-Wsl -Command "hostname -I | awk '{print \$1}'" -NoProfile
Write-Info "WSL IP: $wslIp"

# 添加 Windows 防火墙规则
$ports = @(8000, 5173, 3000, 5432, 6379)
foreach ($port in $ports) {
    $ruleName = "DevFlow-WSL-$port"
    $existing = netsh interface portproxy show v4tov4 | Select-String "$port"
    if (-not $existing) {
        netsh interface portproxy add v4tov4 listenport=$port listenaddress=0.0.0.0 connectport=$port connectaddress=$wslIp | Out-Null
        Write-Info "  端口转发: 0.0.0.0:$port → $wslIp`:$port"
    }
    $fwRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    if (-not $fwRule) {
        New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -LocalPort $port -Protocol TCP -Action Allow | Out-Null
    }
}
Write-OK "端口转发配置完成"

# ── Step 4: 后端部署 ──────────────────────────────────────────────
Write-Step "Step 4/6: 后端环境部署"

if (-not $SkipDocker) {
    # Docker 模式
    Write-Info "启动 Docker 基础设施..."
    Invoke-Wsl -Command @"
cd '$ProjectPath'
if [ "$Mode" = 'docker-dev' ]; then
    docker compose -f docker-compose.dev.yml up -d postgres redis gitea-db gitea 2>&1
else
    docker compose up -d postgres redis 2>&1
fi
"@
    Write-OK "Docker 基础设施已启动"
    Write-Info "等待数据库就绪..."
    Invoke-Wsl -Command "sleep 5"
}

Write-Info "安装 Python 依赖..."
Invoke-Wsl -Command @"
cd '$ProjectPath/backend'

# 安装系统依赖
sudo apt-get update -qq 2>/dev/null
sudo apt-get install -y -qq python3-venv python3-pip libpq-dev gcc 2>/dev/null

# 创建虚拟环境
if [ ! -d '.venv' ] || [ '$Force' = 'True' ]; then
    rm -rf .venv
    python3 -m venv .venv
    echo '[VENV] 虚拟环境已创建'
fi

# 激活并安装依赖
source .venv/bin/activate
pip install --upgrade pip -q 2>/dev/null
pip install -r requirements.txt -q 2>&1

# 安装额外的生产依赖
if [ "$Mode" != 'dev' ]; then
    pip install gunicorn -q 2>/dev/null
fi

echo '[DEPS] Python 依赖安装完成'
"@
Write-OK "Python 依赖安装完成"

# 数据库迁移
Write-Info "执行数据库迁移..."
Invoke-Wsl -Command @"
cd '$ProjectPath/backend'
source .venv/bin/activate
if [ -f alembic.ini ] || [ -d alembic ]; then
    alembic upgrade head 2>&1 || echo '[WARN] 迁移有警告，继续...'
fi
echo '[DB] 数据库迁移完成'
"@
Write-OK "数据库迁移完成"

# ── Step 5: 前端部署 ──────────────────────────────────────────────
if (-not $SkipFrontend) {
    Write-Step "Step 5/6: 前端环境部署"

    Write-Info "安装 Node.js (如需要)..."
    $nodeOk = Test-WslCommand -Command "node --version 2>/dev/null"
    if (-not $nodeOk) {
        Write-Warn "安装 Node.js 22 LTS..."
        Invoke-Wsl -Command @"
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - 2>/dev/null
sudo apt-get install -y -qq nodejs 2>/dev/null
"@ -NoProfile
    }
    Invoke-Wsl -Command "node --version" -NoProfile | ForEach-Object { Write-Info "  Node.js $_" }

    Write-Info "安装前端依赖..."
    Invoke-Wsl -Command @"
cd '$ProjectPath/frontend'
if [ ! -d 'node_modules' ] || [ '$Force' = 'True' ]; then
    npm install 2>&1
fi
echo '[DEPS] 前端依赖安装完成'
"@
    Write-OK "前端依赖安装完成"

    if ($Mode -ne 'dev') {
        Write-Info "构建生产版本..."
        Invoke-Wsl -Command @"
cd '$ProjectPath/frontend'
npm run build 2>&1
echo '[BUILD] 前端构建完成'
"@
        Write-OK "前端构建完成 (dist/)"
    }
} else {
    Write-Info "跳过前端部署"
}

# ── Step 6: 启动服务 ──────────────────────────────────────────────
Write-Step "Step 6/6: 启动服务"

# 先停旧进程
Write-Info "停止已有服务..."
Invoke-Wsl -Command "pkill -f 'uvicorn app.main' 2>/dev/null; pkill -f 'vite' 2>/dev/null; echo 'done'"

# 启动后端
Write-Info "启动 FastAPI 后端..."
if ($Mode -eq 'dev') {
    Invoke-Wsl -Command @"
cd '$ProjectPath/backend'
source .venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/devflow-backend.log 2>&1 &
echo \$! > /tmp/devflow-backend.pid
echo "[OK] Backend PID: \$(cat /tmp/devflow-backend.pid)"
"@
} else {
    # 生产模式用 gunicorn
    Invoke-Wsl -Command @"
cd '$ProjectPath/backend'
source .venv/bin/activate
nohup gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 -w 4 > /tmp/devflow-backend.log 2>&1 &
echo \$! > /tmp/devflow-backend.pid
echo "[OK] Backend PID: \$(cat /tmp/devflow-backend.pid)"
"@
}
Write-OK "后端已启动"

# 启动前端
if (-not $SkipFrontend) {
    if ($Mode -eq 'dev') {
        Write-Info "启动 Vite 前端开发服务器..."
        Invoke-Wsl -Command @"
cd '$ProjectPath/frontend'
nohup npm run dev -- --host 0.0.0.0 > /tmp/devflow-frontend.log 2>&1 &
echo \$! > /tmp/devflow-frontend.pid
echo "[OK] Frontend PID: \$(cat /tmp/devflow-frontend.pid)"
"@
    } else {
        Write-Info "启动 Python HTTP Server 提供前端静态文件..."
        Invoke-Wsl -Command @"
cd '$ProjectPath/frontend/dist'
nohup python3 -m http.server 5173 --bind 0.0.0.0 > /tmp/devflow-frontend.log 2>&1 &
echo \$! > /tmp/devflow-frontend.pid
echo "[OK] Frontend PID: \$(cat /tmp/devflow-frontend.pid)"
"@
    }
    Write-OK "前端已启动"
}

# 等待服务就绪
Write-Info "等待后端就绪..."
$healthy = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $resp = Invoke-Wsl -Command "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health 2>/dev/null" -NoProfile
        if ($resp -eq "200") { $healthy = $true; break }
    } catch { }
    Write-Host "." -NoNewline
    Start-Sleep -Seconds 1
}
Write-Host ""

if ($healthy) {
    Write-OK "后端健康检查通过"
} else {
    Write-Warn "后端可能仍在启动中，稍后重试"
    Write-Info "查看日志: wsl -d $WslDistro -- tail -f /tmp/devflow-backend.log"
}

# ── 部署摘要 ──────────────────────────────────────────────────────
$elapsed = (Get-Date) - $script:StartTime
Write-Host "`n" -NoNewline
Write-Host ("=" * 60) -ForegroundColor Green
Write-Host "  🎉 DevFlow v4.0 部署完成!" -ForegroundColor Green
Write-Host ("=" * 60) -ForegroundColor Green
Write-Host ""
Write-Host "  📍 服务地址:" -ForegroundColor Cyan
Write-Host "    后端 API:   http://localhost:8000" -ForegroundColor White
Write-Host "    API 文档:   http://localhost:8000/docs" -ForegroundColor White
if (-not $SkipFrontend) {
    if ($Mode -eq 'dev') {
        Write-Host "    前端开发:   http://localhost:5173" -ForegroundColor White
    } else {
        Write-Host "    前端:       http://localhost:5173" -ForegroundColor White
    }
}
if (-not $SkipDocker) {
    Write-Host "    Gitea:      http://localhost:3000" -ForegroundColor White
}
Write-Host ""
Write-Host "  🔧 管理命令:" -ForegroundColor Cyan
Write-Host "    查看后端日志: wsl -d $WslDistro -- tail -f /tmp/devflow-backend.log" -ForegroundColor Gray
Write-Host "    查看前端日志: wsl -d $WslDistro -- tail -f /tmp/devflow-frontend.log" -ForegroundColor Gray
Write-Host "    停止所有服务: wsl -d $WslDistro -- bash $ProjectPath/deploy-wsl.sh stop" -ForegroundColor Gray
Write-Host "    重启后端:     wsl -d $WslDistro -- bash $ProjectPath/deploy-wsl.sh restart-backend" -ForegroundColor Gray
Write-Host "    进入 WSL:     wsl -d $WslDistro" -ForegroundColor Gray
Write-Host "    Docker 状态:  wsl -d $WslDistro -- docker compose -f $ProjectPath/docker-compose.dev.yml ps" -ForegroundColor Gray
Write-Host ""
Write-Host "  ⏱️  总耗时: $($elapsed.ToString('mm\:ss'))" -ForegroundColor DarkYellow
Write-Host ("=" * 60) -ForegroundColor Green

# 返回部署状态对象
@{
    Success = $healthy
    WslDistro = $WslDistro
    ProjectPath = $ProjectPath
    WslIp = $wslIp
    Mode = $Mode
    BackendUrl = "http://localhost:8000"
    FrontendUrl = if (-not $SkipFrontend) { "http://localhost:5173" } else { $null }
    ApiDocsUrl = "http://localhost:8000/docs"
    GiteaUrl = if (-not $SkipDocker) { "http://localhost:3000" } else { $null }
    Duration = $elapsed
}