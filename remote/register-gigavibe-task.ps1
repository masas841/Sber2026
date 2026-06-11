# register-gigavibe-task.ps1
# Register a Scheduled Task so GIGAvibe runs independently (survives SSH logout, restarts on boot).
$ErrorActionPreference = "Continue"

$proj = "C:\Users\user\gigavibe"
$startCmd = Join-Path $proj "start-gigavibe-gpu.cmd"
$taskName = "GIGAvibe"
$logDir = "$env:ProgramData\ssh-setup-logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$log = Join-Path $logDir ("gigavibe-task-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".log")

function Write-Log {
    param([string]$m, [string]$lvl = "INFO")
    $line = "[" + (Get-Date -Format "yyyy-MM-dd HH:mm:ss") + "][$lvl] $m"
    Write-Host $line
    Add-Content -Path $log -Value $line -Encoding UTF8
}

# Stop existing server instances on 8765
$conns = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
foreach ($c in $conns) {
    try { Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue; Write-Log "Stopped PID $($c.OwningProcess)" } catch {}
}

# Remove old task
schtasks /Delete /TN $taskName /F 2>$null | Out-Null

$who = (whoami).Trim()
Write-Log "Registering task as user: $who"

# Create via schtasks.exe: at logon, highest privileges, interactive token (no password)
schtasks /Create /TN $taskName /TR "cmd.exe /c `"$startCmd`"" /SC ONLOGON /RL HIGHEST /RU $who /IT /F 2>&1 | ForEach-Object { Write-Log "schtasks: $_" }
Write-Log "Scheduled task '$taskName' registered (ONLOGON, Highest, interactive)."

# Start it now
schtasks /Run /TN $taskName 2>&1 | ForEach-Object { Write-Log "run: $_" }
Write-Log "Task started. Log: $log"
