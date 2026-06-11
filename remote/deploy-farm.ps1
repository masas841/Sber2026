# Деплой GIGAvibe (nanobanana) на FARM + .env + deps + перезапуск
param(
    [string]$Farm = "user@192.168.1.243",
    [string]$EnvTemplate = "farm-nanobanana.env"
)
$ErrorActionPreference = "Stop"
$RemoteRoot = "C:/Users/user/gigavibe"
$LocalGiga = Join-Path $PSScriptRoot "..\gigavibe" | Resolve-Path
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

Write-Host "=== Deploy app/ ===" -ForegroundColor Cyan
Invoke-Scp (Join-Path $LocalGiga "app") "${Farm}:${RemoteRoot}/"

Write-Host "=== Deploy web/ ===" -ForegroundColor Cyan
Invoke-Scp (Join-Path $LocalGiga "web") "${Farm}:${RemoteRoot}/"

Write-Host "=== Deploy assets/ (bg, frames, driving) ===" -ForegroundColor Cyan
Invoke-Scp (Join-Path $LocalGiga "assets") "${Farm}:${RemoteRoot}/"

Write-Host "=== Deploy scripts/ ===" -ForegroundColor Cyan
Invoke-Scp (Join-Path $LocalGiga "scripts") "${Farm}:${RemoteRoot}/"

Write-Host "=== Deploy requirements + constraints ===" -ForegroundColor Cyan
Invoke-Scp (Join-Path $LocalGiga "requirements.txt") "${Farm}:${RemoteRoot}/"
Invoke-Scp (Join-Path $LocalGiga "constraints.txt") "${Farm}:${RemoteRoot}/"

Write-Host "=== Deploy certs ===" -ForegroundColor Cyan
$certsDir = Join-Path $LocalGiga "certs"
Invoke-Scp (Join-Path $certsDir "cert.pem") "${Farm}:${RemoteRoot}/certs/"
Invoke-Scp (Join-Path $certsDir "key.pem") "${Farm}:${RemoteRoot}/certs/"

Write-Host "=== Deploy remote/ scripts ===" -ForegroundColor Cyan
Get-ChildItem $LocalRemote -File | ForEach-Object {
    & scp $_.FullName "${Farm}:${RemoteRoot}/remote/"
    if ($LASTEXITCODE -ne 0) { throw "scp failed: $($_.Name)" }
}

Write-Host "=== Deploy start-gigavibe-gpu.cmd ===" -ForegroundColor Cyan
& scp (Join-Path $LocalRemote "start-gigavibe-gpu.cmd") "${Farm}:${RemoteRoot}/"
if ($LASTEXITCODE -ne 0) { throw "scp start cmd failed" }

Write-Host "=== pip install (httpx + deps) ===" -ForegroundColor Cyan
Invoke-Ssh "cd /d C:\Users\user\gigavibe && .venv\Scripts\python.exe -m pip install -q httpx google-genai cryptography"

Write-Host "=== Apply .env ($EnvTemplate) ===" -ForegroundColor Cyan
Invoke-Ssh "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\user\gigavibe\remote\apply-farm-env.ps1 -EnvTemplate $EnvTemplate"

Write-Host "=== Restart GIGAvibe ===" -ForegroundColor Cyan
Start-Sleep -Seconds 2
Invoke-Ssh "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\user\gigavibe\remote\restart-gigavibe.ps1"

Write-Host "=== Health check ===" -ForegroundColor Cyan
Start-Sleep -Seconds 12
& curl.exe -sk "https://192.168.1.243:8765/api/health"
Write-Host ""
