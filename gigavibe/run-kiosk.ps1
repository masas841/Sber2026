$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

. (Join-Path $PSScriptRoot "install\Resolve-Python.ps1")
. (Join-Path $PSScriptRoot "install\Install-Deps.ps1")

$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    $basePy = Get-GigaPython -Root $PSScriptRoot
    Write-Host "[GIGAvibe] Creating .venv from $basePy ..."
    New-GigaVenv -Root $PSScriptRoot -BasePython $basePy
    & .\.venv\Scripts\Activate.ps1
    Install-GigaKioskDeps -Root $PSScriptRoot
} else {
    & .\.venv\Scripts\Activate.ps1
}

$smileModel = Join-Path $PSScriptRoot "web\models\face_landmarker.task"
if (-not (Test-Path $smileModel)) {
    Write-Host "[GIGAvibe] Smile model missing - run scripts\download_smile_model.ps1" -ForegroundColor Yellow
}

$buffalo = Join-Path $env:USERPROFILE ".insightface\models\buffalo_l\w600k_r50.onnx"
if (-not (Test-Path $buffalo)) {
    Write-Host "[GIGAvibe] buffalo_l missing - run: python scripts\download_buffalo_l.py" -ForegroundColor Yellow
}

if (-not (Test-Path ".env")) {
    if (Test-Path "install\.env.kiosk.example") {
        Copy-Item "install\.env.kiosk.example" ".env"
    } elseif (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
    }
    Write-Host "Created .env - set PUBLIC_BASE_URL and AITUNNEL_API_KEY" -ForegroundColor Yellow
}

Write-Host "Kiosk (portrait): http://127.0.0.1:8765  (health: /api/health)" -ForegroundColor Cyan
python -m app.main
