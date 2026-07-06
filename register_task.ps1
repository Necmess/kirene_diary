# Windows 로그인 시 키레네 디스코드 봇을 자동 실행하는 작업 스케줄러 등록 스크립트
# 사용법: PowerShell을 관리자 권한으로 열고 실행
#   powershell -ExecutionPolicy Bypass -File register_task.ps1

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$startScript = Join-Path $scriptDir "start_cyrene.bat"

if (-not (Test-Path $startScript)) {
    Write-Error "start_cyrene.bat을 찾을 수 없습니다: $startScript"
    exit 1
}

$action = New-ScheduledTaskAction -Execute $startScript -WorkingDirectory $scriptDir
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Days 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName "CyreneDiaryBot" `
    -Action $action -Trigger $trigger -Settings $settings `
    -Description "Windows 로그인 시 키레네 일기 디스코드 봇 자동 실행" `
    -Force

Write-Host "등록 완료. Windows에 로그인하면 자동으로 실행됩니다."
Write-Host "지금 바로 시작하려면: Start-ScheduledTask -TaskName CyreneDiaryBot"
