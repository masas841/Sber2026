# Установка GIGAvibe kiosk (портрет + QR). Python может быть в runtime\python или в системе.
param(
    [switch]$SkipModels,
    [switch]$Offline
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

Write-Host "=== GIGAvibe kiosk install ===" -ForegroundColor Cyan
Write-Host "Root: $Root"

. (Join-Path $PSScriptRoot "Resolve-Python.ps1")
. (Join-Path $PSScriptRoot "Install-Deps.ps1")

$basePy = Get-GigaPython -Root $Root
$ver = & $basePy -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$major, $minor = $ver.Split(".")
if ([int]$major -lt 3 -or ([int]$major -eq 3 -and [int]$minor -lt 10)) {
    throw "Нужен Python 3.10+, найден $ver ($basePy)"
}

if (Test-Path (Join-Path $Root "runtime\python\python.exe")) {
    Write-Host "Python (в комплекте): $basePy ($ver)" -ForegroundColor Green
} else {
    Write-Host "Python (системный): $basePy ($ver)"
}

New-GigaVenv -Root $Root -BasePython $basePy
& .\.venv\Scripts\Activate.ps1

$wheels = Join-Path $Root "install\wheels"
if ($Offline -or (Test-Path $wheels)) {
    if (-not (Test-Path $wheels)) {
        throw "Офлайн-режим: нет папки install\wheels. Соберите пакет с -Offline на машине с интернетом."
    }
    Write-Host "Установка зависимостей из install\wheels (офлайн)…"
    Install-GigaKioskDeps -Root $Root -WheelsDir $wheels
} else {
    Write-Host "Установка зависимостей через pip (нужен интернет)…"
    Install-GigaKioskDeps -Root $Root
}

if (-not $SkipModels) {
    if ($Offline) {
        $smile = Join-Path $Root "web\models\face_landmarker.task"
        if (-not (Test-Path $smile)) {
            Write-Host "WARN: нет web\models\face_landmarker.task — соберите пакет с моделями или -SkipModels" -ForegroundColor Yellow
        }
        $buffalo = Join-Path $env:USERPROFILE ".insightface\models\buffalo_l\w600k_r50.onnx"
        if (-not (Test-Path $buffalo)) {
            Write-Host "WARN: нет buffalo_l — запустите download_buffalo_l на машине с интернетом" -ForegroundColor Yellow
        }
    } else {
        & $Root\scripts\download_smile_model.ps1
        python $Root\scripts\download_buffalo_l.py
    }
}

if (-not (Test-Path ".env")) {
    Copy-Item $PSScriptRoot\.env.kiosk.example .env
    Write-Host "Создан .env — укажите PUBLIC_BASE_URL и AITUNNEL_API_KEY" -ForegroundColor Yellow
}

New-Item -ItemType Directory -Force -Path "$Root\data\outputs" | Out-Null
New-Item -ItemType Directory -Force -Path "$Root\data\uploads" | Out-Null

Write-Host ""
Write-Host "Готово. Запуск:" -ForegroundColor Green
Write-Host "  .\run-kiosk.ps1"
Write-Host "  или install\start-gigavibe.cmd"
Write-Host "Киоск: http://127.0.0.1:8765"
