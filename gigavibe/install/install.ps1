# Install GIGAvibe kiosk (portrait + QR). Python can be bundled in runtime\python or installed system-wide.
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
. (Join-Path $PSScriptRoot "Install-VCRedist.ps1")
. (Join-Path $PSScriptRoot "Update-EnvDefaults.ps1")

$basePy = Get-GigaPython -Root $Root
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

Ensure-GigaVcRedist -Root $Root -Offline:$Offline

New-GigaVenv -Root $Root -BasePython $basePy
& .\.venv\Scripts\Activate.ps1

$wheels = Join-Path $Root "install\wheels"
if ($Offline -or (Test-Path $wheels)) {
    if (-not (Test-Path $wheels)) {
        throw "Offline mode: install\wheels is missing. Build the package with -Offline on a machine with internet access."
    }
    Write-Host "Installing dependencies from install\wheels (offline) ..."
    Install-GigaKioskDeps -Root $Root -WheelsDir $wheels
} else {
    Write-Host "Installing dependencies with pip (internet required) ..."
    Install-GigaKioskDeps -Root $Root
}

if (-not $SkipModels) {
    if ($Offline) {
        $smile = Join-Path $Root "web\models\face_landmarker.task"
        if (-not (Test-Path $smile)) {
            Write-Host "WARN: web\models\face_landmarker.task is missing - build with models or use -SkipModels" -ForegroundColor Yellow
        }
        $buffalo = Join-Path $env:USERPROFILE ".insightface\models\buffalo_l\w600k_r50.onnx"
        if (-not (Test-Path $buffalo)) {
            Write-Host "WARN: buffalo_l is missing - run download_buffalo_l on a machine with internet access" -ForegroundColor Yellow
        }
    } else {
        & $Root\scripts\download_smile_model.ps1
        python $Root\scripts\download_buffalo_l.py
        if ($LASTEXITCODE -ne 0) {
            throw "buffalo_l download failed"
        }
        python -m scripts.check_onnx_cuda
        if ($LASTEXITCODE -ne 0) {
            throw "CUDAExecutionProvider is not active. Install NVIDIA driver 531.14+ for CUDA 12.1 support."
        }
    }
}

if (-not (Test-Path ".env")) {
    Copy-Item $PSScriptRoot\.env.kiosk.example .env
    Write-Host "Created .env - set PUBLIC_BASE_URL and AITUNNEL_API_KEY" -ForegroundColor Yellow
}
Update-GigaEnvDefaults -Root $Root

New-Item -ItemType Directory -Force -Path "$Root\data\outputs" | Out-Null
New-Item -ItemType Directory -Force -Path "$Root\data\uploads" | Out-Null

Write-Host ""
Write-Host "Done. Run:" -ForegroundColor Green
Write-Host "  .\run-kiosk.ps1"
Write-Host "  or install\start-gigavibe.cmd"
Write-Host "Kiosk: http://127.0.0.1:8765"
