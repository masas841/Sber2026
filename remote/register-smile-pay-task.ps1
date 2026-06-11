# Scheduled Task: Smile Pay on port 8767 (survives SSH logout).
$ErrorActionPreference = "Continue"

$proj = "C:\Users\user\smile-pay"
$startCmd = Join-Path $proj "start-smile-pay.cmd"
$taskName = "SmilePay"
$logDir = "$env:ProgramData\ssh-setup-logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$log = Join-Path $logDir ("smile-pay-task-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".log")

function Write-Log {
    param([string]$m, [string]$lvl = "INFO")
    $line = "[" + (Get-Date -Format "yyyy-MM-dd HH:mm:ss") + "][$lvl] $m"
    Write-Host $line
    Add-Content -Path $log -Value $line -Encoding UTF8
}

$conns = Get-NetTCPConnection -LocalPort 8767 -State Listen -ErrorAction SilentlyContinue
foreach ($c in $conns) {
    try { Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue; Write-Log "Stopped PID $($c.OwningProcess)" } catch {}
}

schtasks /Delete /TN $taskName /F 2>$null | Out-Null

$who = (whoami).Trim()
Write-Log "Registering task as user: $who"

schtasks /Create /TN $taskName /TR "cmd.exe /c `"$startCmd`"" /SC ONLOGON /RL HIGHEST /RU $who /IT /F 2>&1 | ForEach-Object { Write-Log "schtasks: $_" }
Write-Log "Scheduled task '$taskName' registered (ONLOGON, Highest, interactive)."

schtasks /Run /TN $taskName 2>&1 | ForEach-Object { Write-Log "run: $_" }
Write-Log "Task started. Log: $log"
