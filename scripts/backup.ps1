# DevFlow 自动备份脚本 (PowerShell版本)
# 用途：备份PostgreSQL、Redis、Gitea数据和Docker Volume

param(
    [int]$RetentionDays = 7
)

$ErrorActionPreference = "Stop"

# 配置
$BackupRoot = "E:\code\DevFlow\backups"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupDir = "$BackupRoot\$Timestamp"
$LogFile = "$BackupRoot\backup.log"
$ProjectRoot = "E:\code\DevFlow"

# 颜色输出函数
function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] $Message"
    Write-Host $logMessage
    Add-Content -Path $LogFile -Value $logMessage
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
    Write-Log "[SUCCESS] $Message"
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
    Write-Log "[WARN] $Message"
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
    Write-Log "[ERROR] $Message"
    exit 1
}

# 创建备份目录
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
Write-Log "开始备份 - $Timestamp"
Write-Log "备份目录: $BackupDir"

# 检查Docker服务
try {
    docker info | Out-Null
} catch {
    Write-Error "Docker服务未运行"
}

# 检查容器状态
function Test-Container {
    param([string]$ContainerName)
    $container = docker ps --filter "name=$ContainerName" --filter "status=running" -q
    if (-not $container) {
        Write-Warning "容器 $ContainerName 未运行，跳过备份"
        return $false
    }
    return $true
}

# 1. 备份PostgreSQL数据库
function Backup-Postgres {
    Write-Log "备份PostgreSQL数据库..."
    
    if (Test-Container "devflow-postgres") {
        try {
            # SQL备份
            $sqlBackup = "$BackupDir\devflow_db.sql"
            docker exec devflow-postgres pg_dump -U devflow_user devflow_db > $sqlBackup 2>&1
            
            # 压缩SQL文件
            Compress-Archive -Path $sqlBackup -DestinationPath "$BackupDir\devflow_db.zip" -Force
            Remove-Item $sqlBackup
            Write-Success "PostgreSQL数据库备份完成: devflow_db.zip"
            
            # Volume备份
            docker run --rm `
                -v devflow_postgres_data:/data:ro `
                -v "${BackupDir}:/backup" `
                alpine tar czf /backup/postgres_volume.tar.gz /data 2>&1 | Out-Null
            
            Write-Success "PostgreSQL Volume备份完成: postgres_volume.tar.gz"
        } catch {
            Write-Error "PostgreSQL备份失败: $_"
        }
    }
}

# 2. 备份Redis数据
function Backup-Redis {
    Write-Log "备份Redis数据..."
    
    if (Test-Container "devflow-redis") {
        try {
            # 触发RDB快照
            docker exec devflow-redis redis-cli BGSAVE | Out-Null
            
            # 等待快照完成
            Start-Sleep -Seconds 5
            
            # Volume备份
            docker run --rm `
                -v devflow_redis_data:/data:ro `
                -v "${BackupDir}:/backup" `
                alpine tar czf /backup/redis_volume.tar.gz /data 2>&1 | Out-Null
            
            Write-Success "Redis Volume备份完成: redis_volume.tar.gz"
        } catch {
            Write-Error "Redis备份失败: $_"
        }
    }
}

# 3. 备份Gitea数据
function Backup-Gitea {
    Write-Log "备份Gitea数据..."
    
    if (Test-Container "devflow-gitea") {
        try {
            # Gitea数据Volume
            docker run --rm `
                -v devflow_gitea_data:/data:ro `
                -v "${BackupDir}:/backup" `
                alpine tar czf /backup/gitea_data.tar.gz /data 2>&1 | Out-Null
            
            Write-Success "Gitea数据备份完成: gitea_data.tar.gz"
            
            # Gitea数据库Volume
            if (Test-Container "devflow-gitea-db") {
                docker run --rm `
                    -v devflow_gitea_db_data:/data:ro `
                    -v "${BackupDir}:/backup" `
                    alpine tar czf /backup/gitea_db_volume.tar.gz /data 2>&1 | Out-Null
                
                Write-Success "Gitea数据库备份完成: gitea_db_volume.tar.gz"
            }
        } catch {
            Write-Error "Gitea备份失败: $_"
        }
    }
}

# 4. 备份环境配置
function Backup-Config {
    Write-Log "备份环境配置..."
    
    $configDir = "$BackupDir\config"
    New-Item -ItemType Directory -Force -Path $configDir | Out-Null
    
    # 备份.env文件
    if (Test-Path "$ProjectRoot\.env") {
        Copy-Item "$ProjectRoot\.env" "$configDir\.env"
    }
    
    if (Test-Path "$ProjectRoot\.env.production") {
        Copy-Item "$ProjectRoot\.env.production" "$configDir\.env.production"
    }
    
    # 备份docker-compose配置
    Copy-Item "$ProjectRoot\docker-compose.yml" "$configDir\docker-compose.yml"
    
    # 备份Nginx配置
    if (Test-Path "$ProjectRoot\docker\nginx") {
        Copy-Item -Recurse "$ProjectRoot\docker\nginx" "$configDir\nginx"
    }
    
    Write-Success "配置文件备份完成"
}

# 5. 创建备份清单
function New-Manifest {
    Write-Log "创建备份清单..."
    
    $manifest = @{
        timestamp = $Timestamp
        date = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        version = "1.0"
        containers = @{
            postgres = (docker inspect devflow-postgres --format='{{.State.Status}}' 2>$null)
            redis = (docker inspect devflow-redis --format='{{.State.Status}}' 2>$null)
            gitea = (docker inspect devflow-gitea --format='{{.State.Status}}' 2>$null)
            backend = (docker inspect devflow-backend --format='{{.State.Status}}' 2>$null)
        }
        files = (Get-ChildItem $BackupDir -File | Select-Object -ExpandProperty Name)
    }
    
    $manifest | ConvertTo-Json | Out-File "$BackupDir\manifest.json"
    Write-Success "备份清单创建完成: manifest.json"
}

# 6. 清理旧备份
function Remove-OldBackups {
    Write-Log "清理超过 $RetentionDays 天的旧备份..."
    
    $cutoffDate = (Get-Date).AddDays(-$RetentionDays)
    
    Get-ChildItem $BackupRoot -Directory | Where-Object {
        $_.Name -match "^\d{8}_\d{6}$" -and $_.CreationTime -lt $cutoffDate
    } | Remove-Item -Recurse -Force
    
    # 只保留最近10个备份
    $backups = Get-ChildItem $BackupRoot -Directory | 
        Where-Object { $_.Name -match "^\d{8}_\d{6}$" } | 
        Sort-Object CreationTime -Descending
    
    if ($backups.Count -gt 10) {
        $backups | Select-Object -Skip 10 | Remove-Item -Recurse -Force
    }
    
    Write-Success "旧备份清理完成"
}

# 7. 计算备份大小
function Get-BackupSize {
    $size = (Get-ChildItem $BackupDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Success "备份大小: $([math]::Round($size, 2)) MB"
}

# 主备份流程
Backup-Postgres
Backup-Redis
Backup-Gitea
Backup-Config
New-Manifest
Get-BackupSize
Remove-OldBackups

Write-Log "备份完成！"
Write-Log "备份位置: $BackupDir"

# 返回备份路径
return $BackupDir
