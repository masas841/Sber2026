# Deploy SberKopilka to FARM (port 8766)
param(
    [string]$Farm = "user@192.168.1.243"
)
$ErrorActionPreference = "Stop"
$RemoteRoot = "C:/Users/user/sberkopilka"
$LocalRoot = Join-Path $PSScriptRoot "..\sberkopilka" | Resolve-Path
$LocalRemote = $PSScriptRoot | Resolve-Path

function Invoke-Scp {
    param([string]$Source, [string]$Dest)
    & scp -r $Source $Dest
    if ($LASTEXITCODE -ne 0) { throw "scp failed: $Source -> $Dest" }
}

function Invoke-Ssh {
    param([string]$Command)
    & ssh $Farm $Command
    if ($LASTEXITCODE -ne 0) { throw "ssh failed: $Command" }
}

Write-Host "=== Ensure remote dirs ===" -ForegroundColor Cyan
Invoke-Ssh "if not exist C:\Users\user\sberkopilka\remote mkdir C:\Users\user\sberkopilka\remote & if not exist C:\Users\user\sberkopilka\data mkdir C:\Users\user\sberkopilka\data & exit 0"

Write-Host "=== Pack app/ + web/ + requirements.txt ===" -ForegroundColor Cyan
$Archive = Join-Path $env:TEMP "sberkopilka-deploy.tar.gz"
if (Test-Path $Archive) { Remove-Item $Archive -Force }
& tar -czf $Archive -C "$LocalRoot" --exclude="__pycache__" --exclude="*.pyc" app web requirements.txt
if ($LASTEXITCODE -ne 0) { throw "tar pack failed" }
Write-Host ("archive: {0:N1} MB" -f ((Get-Item $Archive).Length / 1MB))

Write-Host "=== Upload archive ===" -ForegroundColor Cyan
Invoke-Scp $Archive "${Farm}:${RemoteRoot}/deploy.tar.gz"

Write-Host "=== Extract on farm ===" -ForegroundColor Cyan
Invoke-Ssh "cd /d C:\Users\user\sberkopilka & tar -xzf deploy.tar.gz & del deploy.tar.gz & exit 0"

Write-Host "=== Deploy remote scripts ===" -ForegroundColor Cyan
$remoteFiles = @(
    "farm-sberkopilka.env",
    "start-sberkopilka.cmd",
    "setup-sberkopilka-farm.ps1",
    "register-sberkopilka-task.ps1",
    "restart-sberkopilka.ps1"
)
foreach ($name in $remoteFiles) {
    & scp (Join-Path $LocalRemote $name) "${Farm}:${RemoteRoot}/remote/"
    if ($LASTEXITCODE -ne 0) { throw "scp failed: $name" }
}

& scp (Join-Path $LocalRemote "start-sberkopilka.cmd") "${Farm}:${RemoteRoot}/"
if ($LASTEXITCODE -ne 0) { throw "scp start cmd failed" }

Write-Host "=== Setup venv, .env, firewall, task ===" -ForegroundColor Cyan
Invoke-Ssh "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\user\sberkopilka\remote\setup-sberkopilka-farm.ps1"

Write-Host "=== Restart SberKopilka ===" -ForegroundColor Cyan
Start-Sleep -Seconds 2
Invoke-Ssh "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\user\sberkopilka\remote\restart-sberkopilka.ps1"

Write-Host "=== Health check ===" -ForegroundColor Cyan
Start-Sleep -Seconds 8
& curl.exe -s "http://192.168.1.243:8766/api/health"
Write-Host ""
Write-Host "SberKopilka: http://192.168.1.243:8766" -ForegroundColor Green
