param(
    [switch]$UpdateFromGitHub,
    [switch]$SkipUpdate
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Read-DotEnvValue {
    param(
        [string]$Path,
        [string]$Name
    )

    if (-not (Test-Path $Path)) { return $null }
    $pattern = "^\s*$([regex]::Escape($Name))\s*=\s*(.*)\s*$"
    foreach ($line in Get-Content -Path $Path) {
        if ($line -match "^\s*#") { continue }
        if ($line -match $pattern) {
            return $matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return $null
}

function Test-DotEnvBool {
    param(
        [string]$Path,
        [string]$Name
    )

    $value = Read-DotEnvValue -Path $Path -Name $Name
    if (-not $value) { return $false }
    return $value -match "^(1|true|yes|on)$"
}

$envPath = Join-Path $PSScriptRoot ".env"
$autoUpdate = Test-DotEnvBool -Path $envPath -Name "AUTO_UPDATE_FROM_GITHUB"
if (-not $SkipUpdate -and ($UpdateFromGitHub -or $autoUpdate)) {
    $updater = Join-Path $PSScriptRoot "install\update-from-github.ps1"
    if (Test-Path $updater) {
        Write-Host "[GIGAvibe] Checking GitHub update ..." -ForegroundColor Cyan
        & $updater
    } else {
        Write-Host "[GIGAvibe] Updater not found: $updater" -ForegroundColor Yellow
    }
}

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

$buffalo = Join-Path $PSScriptRoot "models\insightface\models\buffalo_l\w600k_r50.onnx"
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

$envDefaults = Join-Path $PSScriptRoot "install\Update-EnvDefaults.ps1"
if (Test-Path $envDefaults) {
    . $envDefaults
    Update-GigaEnvDefaults -Root $PSScriptRoot
    Ensure-GigaMediaPipeVendor -Root $PSScriptRoot
}

$torchLib = & python -c "import os, torch; print(os.path.join(os.path.dirname(torch.__file__), 'lib'))" 2>$null
if ($LASTEXITCODE -eq 0 -and $torchLib -and (Test-Path $torchLib)) {
    $env:PATH = "$torchLib;$env:PATH"
    Write-Host "[GIGAvibe] CUDA DLL path: $torchLib"
} else {
    Write-Host "[GIGAvibe] WARN: torch CUDA DLL path not found; ONNX CUDA provider may fail" -ForegroundColor Yellow
}

Write-Host "Kiosk (portrait): http://127.0.0.1:8765  (health: /api/health)" -ForegroundColor Cyan
python -m app.main
