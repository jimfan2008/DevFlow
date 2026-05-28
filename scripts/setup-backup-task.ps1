# DevFlow 定时备份任务设置脚本
# 用途：创建Windows任务计划，自动执行每日备份

$ErrorActionPreference = "Stop"

$TaskName = "DevFlow-Daily-Backup"
$TaskDescription = "DevFlow项目每日自动备份任务"
$ScriptPath = "E:\code\DevFlow\scripts\backup.ps1"
$BackupLog = "E:\code\DevFlow\backups\task.log"

Write-Host "=== DevFlow 定时备份任务设置 ===" -ForegroundColor Cyan
Write-Host ""

# 检查脚本是否存在
if (-not (Test-Path $ScriptPath)) {
    Write-Host "错误: 备份脚本不存在: $ScriptPath" -ForegroundColor Red
    exit 1
}

# 检查是否已存在同名任务
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "警告: 任务 '$TaskName' 已存在" -ForegroundColor Yellow
    $overwrite = Read-Host "是否覆盖现有任务？(yes/no)"
    
    if ($overwrite -eq "yes") {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "已删除现有任务" -ForegroundColor Green
    } else {
        Write-Host "取消设置" -ForegroundColor Yellow
        exit 0
    }
}

Write-Host "创建定时备份任务..." -ForegroundColor Cyan

# 创建任务触发器（每天凌晨2点执行）
$trigger = New-ScheduledTaskTrigger -Daily -At 2am

# 创建任务动作
$action = New-ScheduledTaskAction `
    -Execute "PowerShell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`"" `
    -WorkingDirectory "E:\code\DevFlow\scripts"

# 创建任务设置
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable:$false `
    -MultipleInstances DontAllowNew

# 创建主体（以当前用户身份运行）
$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Highest

# 注册任务
Register-ScheduledTask `
    -TaskName $TaskName `
    -TaskPath "\DevFlow" `
    -Description $TaskDescription `
    -Trigger $trigger `
    -Action $action `
    -Settings $settings `
    -Principal $principal

Write-Host ""
Write-Host "✅ 定时备份任务创建成功！" -ForegroundColor Green
Write-Host ""

# 显示任务信息
$task = Get-ScheduledTask -TaskName $TaskName
Write-Host "任务信息:" -ForegroundColor Cyan
Write-Host "  名称: $($task.TaskName)"
Write-Host "  描述: $($task.Description)"
Write-Host "  触发器: $($task.Triggers[0].ToString())"
Write-Host "  状态: $($task.State)"
Write-Host "  下次运行: $($task.NextRunTime)"
Write-Host ""

# 询问是否立即测试
$testNow = Read-Host "是否立即测试备份？(yes/no)"
if ($testNow -eq "yes") {
    Write-Host ""
    Write-Host "执行备份测试..." -ForegroundColor Cyan
    
    try {
        & $ScriptPath
        Write-Host ""
        Write-Host "✅ 备份测试成功！" -ForegroundColor Green
    } catch {
        Write-Host ""
        Write-Host "❌ 备份测试失败: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== 设置完成 ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "管理命令:" -ForegroundColor Yellow
Write-Host "  查看任务: Get-ScheduledTask -TaskName '$TaskName'"
Write-Host "  手动运行: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "  禁用任务: Disable-ScheduledTask -TaskName '$TaskName'"
Write-Host "  启用任务: Enable-ScheduledTask -TaskName '$TaskName'"
Write-Host "  删除任务: Unregister-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "备份文件位置: E:\code\DevFlow\backups" -ForegroundColor Green
