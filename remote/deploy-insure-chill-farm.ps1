# Deploy Insure Chill to FARM (port 8768)
param(
    [string]$Farm = "user@192.168.1.243"
)
$ErrorActionPreference = "Stop"
$RemoteRoot = "C:/Users/user/insure-chill"
$LocalRoot = Join-Path $PSScriptRoot "..\insure-chill" | Resolve-Path
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
Invoke-Ssh "if not exist C:\Users\user\insure-chill\remote mkdir C:\Users\user\insure-chill\remote & exit 0"

Write-Host "=== Pack app/ + static/ + img/ + scripts/ + requirements.txt ===" -ForegroundColor Cyan
$Archive = Join-Path $env:TEMP "insure-chill-deploy.tar.gz"
if (Test-Path $Archive) { Remove-Item $Archive -Force }
& tar -czf $Archive -C "$LocalRoot" --exclude="__pycache__" --exclude="*.pyc" app static img scripts/gen_self_signed_cert.py scripts/__init__.py requirements.txt
if ($LASTEXITCODE -ne 0) { throw "tar pack failed" }
Write-Host ("archive: {0:N1} MB" -f ((Get-Item $Archive).Length / 1MB))

Write-Host "=== Upload archive ===" -ForegroundColor Cyan
Invoke-Scp $Archive "${Farm}:${RemoteRoot}/deploy.tar.gz"

Write-Host "=== Extract on farm ===" -ForegroundColor Cyan
Invoke-Ssh "cd /d C:\Users\user\insure-chill & tar -xzf deploy.tar.gz & del deploy.tar.gz & exit 0"

Write-Host "=== Deploy remote scripts ===" -ForegroundColor Cyan
$remoteFiles = @(
    "farm-insure-chill.env",
    "start-insure-chill.cmd",
    "setup-insure-chill-farm.ps1",
    "register-insure-chill-task.ps1",
    "restart-insure-chill.ps1"
)
foreach ($name in $remoteFiles) {
    & scp (Join-Path $LocalRemote $name) "${Farm}:${RemoteRoot}/remote/"
    if ($LASTEXITCODE -ne 0) { throw "scp failed: $name" }
}

& scp (Join-Path $LocalRemote "start-insure-chill.cmd") "${Farm}:${RemoteRoot}/"
if ($LASTEXITCODE -ne 0) { throw "scp start cmd failed" }

Write-Host "=== Setup venv, .env, firewall, task ===" -ForegroundColor Cyan
Invoke-Ssh "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\user\insure-chill\remote\setup-insure-chill-farm.ps1"

Write-Host "=== Restart Insure Chill ===" -ForegroundColor Cyan
Start-Sleep -Seconds 2
Invoke-Ssh "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\user\insure-chill\remote\restart-insure-chill.ps1"

Write-Host "=== Health check ===" -ForegroundColor Cyan
Start-Sleep -Seconds 8
& curl.exe -sk "https://192.168.1.243:8768/api/health"
Write-Host ""
Write-Host "Insure Chill screen:  https://slash.omelchak.com:8768/" -ForegroundColor Green
Write-Host "Insure Chill tablet:  https://slash.omelchak.com:8768/control" -ForegroundColor Green
Write-Host "LAN:                  https://192.168.1.243:8768/" -ForegroundColor Green
