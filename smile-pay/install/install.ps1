# Install Smile Pay kiosk. Python can be bundled in runtime\python or installed system-wide.
param(
    [switch]$Offline
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$Monorepo = Split-Path $Root -Parent
$Kiosk = Join-Path $Monorepo "scripts\kiosk"
Set-Location $Root

Write-Host "=== Smile Pay kiosk install ===" -ForegroundColor Cyan
Write-Host "Root: $Root"

. (Join-Path $Kiosk "Resolve-Python.ps1")
. (Join-Path $Kiosk "Install-PipDeps.ps1")
. (Join-Path $PSScriptRoot "Update-EnvDefaults.ps1")

$basePy = Get-KioskPython -Root $Root
$ver = & $basePy -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$major, $minor = $ver.Split(".")
if ([int]$major -lt 3 -or ([int]$major -eq 3 -and [int]$minor -lt 10)) {
    throw "Python 3.10+ is required, found $ver ($basePy)"
}

if (Test-Path (Join-Path $Root "runtime\python\python.exe")) {
    Write-Host "Python (bundled): $basePy ($ver)" -ForegroundColor Green
} else {
    Write-Host "Python (system): $basePy ($ver)"
}

New-KioskVenv -Root $Root -BasePython $basePy
& .\.venv\Scripts\Activate.ps1

$wheels = Join-Path $Root "install\wheels"
if ($Offline -or (Test-Path $wheels)) {
    if (-not (Test-Path $wheels)) {
        throw "Offline mode: install\wheels is missing. Build the package with -Offline on a machine with internet access."
    }
    Write-Host "Installing dependencies from install\wheels (offline) ..."
    Install-KioskPipDeps -Root $Root -WheelsDir $wheels
} else {
    Write-Host "Installing dependencies with pip (internet required) ..."
    Install-KioskPipDeps -Root $Root
}

if ($Offline) {
    $smile = Join-Path $Root "web\models\face_landmarker.task"
    $bundle = Join-Path $Root "web\vendor\mediapipe\tasks-vision\vision_bundle.mjs"
    if (-not (Test-Path $smile)) {
        Write-Host "WARN: web\models\face_landmarker.task is missing - build offline package with internet first" -ForegroundColor Yellow
    }
    if (-not (Test-Path $bundle)) {
        Write-Host "WARN: MediaPipe vendor is missing - build offline package with internet first" -ForegroundColor Yellow
    }
} else {
    Ensure-SmilePayMediaPipeVendor -Root $Root
    Ensure-SmilePayFaceModel -Root $Root
}

if (-not (Test-Path ".env")) {
    Copy-Item $PSScriptRoot\.env.kiosk.example .env
    Write-Host "Created .env from install\.env.kiosk.example" -ForegroundColor Yellow
}
Update-SmilePayEnvDefaults -Root $Root

New-Item -ItemType Directory -Force -Path "$Root\data" | Out-Null

Write-Host ""
Write-Host "Done. Run:" -ForegroundColor Green
Write-Host "  .\run-kiosk.ps1"
Write-Host "  or install\start-smile-pay.cmd"
Write-Host "Kiosk: http://127.0.0.1:8888"
