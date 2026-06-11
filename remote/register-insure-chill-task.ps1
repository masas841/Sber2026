# Scheduled Task: Insure Chill on port 8768 (survives SSH logout).
$ErrorActionPreference = "Continue"

$proj = "C:\Users\user\insure-chill"
$startCmd = Join-Path $proj "start-insure-chill.cmd"
$taskName = "InsureChill"
$logDir = "$env:ProgramData\ssh-setup-logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$log = Join-Path $logDir ("insure-chill-task-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".log")

function Write-Log {
    param([string]$m, [string]$lvl = "INFO")
    $line = "[" + (Get-Date -Format "yyyy-MM-dd HH:mm:ss") + "][$lvl] $m"
    Write-Host $line
    Add-Content -Path $log -Value $line -Encoding UTF8
}

$conns = Get-NetTCPConnection -LocalPort 8768 -State Listen -ErrorAction SilentlyContinue
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
