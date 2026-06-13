# Деплой photo_receiver на Greathearted Inna + обновление FARM
param(
    [string]$PhotoHost = "root@45.67.59.125",
    [string]$Farm = "user@192.168.1.243",
    [string]$RemoteDir = "/opt/photo-receiver",
    [int]$Port = 8767,
    [string]$PublicUrl = "https://sberfest2026.ru"
)
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$LocalReceiver = Join-Path $Root "photo_receiver"
$LocalGiga = Join-Path $Root "gigavibe"

if (-not (Test-Path $LocalReceiver)) {
    throw "Не найден $LocalReceiver"
}

Write-Host "=== Deploy photo_receiver -> $PhotoHost ===" -ForegroundColor Cyan
ssh -o StrictHostKeyChecking=accept-new $PhotoHost "mkdir -p $RemoteDir"
scp -r "$LocalReceiver\app" "${PhotoHost}:${RemoteDir}/"
scp -r "$LocalReceiver\static" "${PhotoHost}:${RemoteDir}/"
scp "$LocalReceiver\requirements.txt" "${PhotoHost}:${RemoteDir}/"
scp "$LocalReceiver\.env.example" "${PhotoHost}:${RemoteDir}/"
scp "$LocalReceiver\install.sh" "${PhotoHost}:${RemoteDir}/"
ssh $PhotoHost "chmod +x $RemoteDir/install.sh && PUBLIC_URL=$PublicUrl PORT=$Port bash $RemoteDir/install.sh $RemoteDir"

Write-Host "=== Health photo receiver ===" -ForegroundColor Cyan
curl.exe -sf "$PublicUrl/api/health"
Write-Host ""

Write-Host "=== Deploy GIGAvibe upload client -> FARM ===" -ForegroundColor Cyan
$files = @(
    "app\config.py",
    "app\output_dispatch.py",
    "app\upload_client.py",
    "app\upload_queue.py",
    "app\qr_util.py",
    "app\pipeline.py",
    "app\main.py"
)
foreach ($f in $files) {
    scp (Join-Path $LocalGiga $f) "${Farm}:C:/Users/user/gigavibe/$($f -replace '\\','/')"
}
scp (Join-Path $PSScriptRoot "farm-nanobanana.env") "${Farm}:C:/Users/user/gigavibe/remote/farm-nanobanana.env"
ssh $Farm "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\user\gigavibe\remote\apply-farm-env.ps1 -EnvTemplate farm-nanobanana.env"
ssh $Farm "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\user\gigavibe\remote\restart-gigavibe.ps1"

Start-Sleep 10
Write-Host "=== FARM health ===" -ForegroundColor Cyan
curl.exe -sk "https://192.168.1.243:8765/api/health"
Write-Host ""
