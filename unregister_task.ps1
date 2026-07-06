# 등록된 자동 실행 작업을 제거한다.
# 사용법: powershell -ExecutionPolicy Bypass -File unregister_task.ps1

$ErrorActionPreference = "Stop"

if (Get-ScheduledTask -TaskName "CyreneDiaryBot" -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName "CyreneDiaryBot" -Confirm:$false
    Write-Host "CyreneDiaryBot 작업을 제거했습니다."
} else {
    Write-Host "등록된 CyreneDiaryBot 작업이 없습니다."
}
