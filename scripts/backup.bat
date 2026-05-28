@echo off
REM DevFlow 简单备份脚本 (Windows Batch)
REM 用途：快速备份PostgreSQL、Redis、Gitea数据

setlocal enabledelayedexpansion

REM 配置
set BACKUP_ROOT=E:\code\DevFlow\backups
set TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set BACKUP_DIR=%BACKUP_ROOT%\%TIMESTAMP%
set LOG_FILE=%BACKUP_ROOT%\backup.log

REM 创建备份目录
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

echo [%date% %time%] 开始备份 - %TIMESTAMP% >> "%LOG_FILE%"
echo 备份目录: %BACKUP_DIR%
echo.

REM 1. 备份PostgreSQL数据库
echo [1/4] 备份PostgreSQL数据库...
docker exec devflow-postgres pg_dump -U devflow_user devflow_db > "%BACKUP_DIR%\devflow_db.sql" 2>&1
if %errorlevel% equ 0 (
    echo     成功: devflow_db.sql
    echo [%date% %time%] PostgreSQL备份成功 >> "%LOG_FILE%"
) else (
    echo     失败!
    echo [%date% %time%] PostgreSQL备份失败 >> "%LOG_FILE%"
)

REM 2. 备份Redis数据
echo [2/4] 备份Redis数据...
docker exec devflow-redis redis-cli BGSAVE > nul 2>&1
timeout /t 3 /nobreak > nul
docker cp devflow-redis:/data/dump.rdb "%BACKUP_DIR%\redis_dump.rdb" 2>&1
if %errorlevel% equ 0 (
    echo     成功: redis_dump.rdb
    echo [%date% %time%] Redis备份成功 >> "%LOG_FILE%"
) else (
    echo     失败!
    echo [%date% %time%] Redis备份失败 >> "%LOG_FILE%"
)

REM 3. 备份Gitea数据
echo [3/4] 备份Gitea数据...
docker exec devflow-gitea tar czf /tmp/gitea_backup.tar.gz /data 2>&1
docker cp devflow-gitea:/tmp/gitea_backup.tar.gz "%BACKUP_DIR%\gitea_data.tar.gz" 2>&1
if %errorlevel% equ 0 (
    echo     成功: gitea_data.tar.gz
    echo [%date% %time%] Gitea备份成功 >> "%LOG_FILE%"
) else (
    echo     失败!
    echo [%date% %time%] Gitea备份失败 >> "%LOG_FILE%"
)

REM 4. 备份配置文件
echo [4/4] 备份配置文件...
if not exist "%BACKUP_DIR%\config" mkdir "%BACKUP_DIR%\config"
copy "E:\code\DevFlow\.env" "%BACKUP_DIR%\config\.env" > nul 2>&1
copy "E:\code\DevFlow\.env.production" "%BACKUP_DIR%\config\.env.production" > nul 2>&1
copy "E:\code\DevFlow\docker-compose.yml" "%BACKUP_DIR%\config\docker-compose.yml" > nul 2>&1
echo     成功: config/
echo [%date% %time%] 配置文件备份成功 >> "%LOG_FILE%"

REM 5. 创建备份清单
echo. > "%BACKUP_DIR%\manifest.txt"
echo 备份时间: %TIMESTAMP% >> "%BACKUP_DIR%\manifest.txt"
echo 备份日期: %date% %time% >> "%BACKUP_DIR%\manifest.txt"
echo. >> "%BACKUP_DIR%\manifest.txt"
echo 文件列表: >> "%BACKUP_DIR%\manifest.txt"
dir /b "%BACKUP_DIR%" >> "%BACKUP_DIR%\manifest.txt"

REM 6. 压缩备份
echo.
echo 压缩备份文件...
powershell Compress-Archive -Path "%BACKUP_DIR%\*" -DestinationPath "%BACKUP_DIR%.zip" -Force

REM 7. 计算大小
for /f "tokens=3" %%a in ('dir /-c "%BACKUP_DIR%.zip" ^| find "字节"') do set SIZE=%%a
set /a SIZE_MB=%SIZE%/1024/1024
echo 备份大小: %SIZE_MB% MB

REM 8. 清理旧备份 (保留最近7天)
echo.
echo 清理旧备份...
forfiles /P "%BACKUP_ROOT%" /M *.zip /D -7 /C "cmd /c del @path" 2>nul

echo.
echo ========================================
echo 备份完成！
echo 备份位置: %BACKUP_DIR%.zip
echo 备份大小: %SIZE_MB% MB
echo ========================================
echo [%date% %time%] 备份完成，大小: %SIZE_MB%MB >> "%LOG_FILE%"

REM 返回备份路径
echo.
echo 备份文件: %BACKUP_DIR%.zip

endlocal
