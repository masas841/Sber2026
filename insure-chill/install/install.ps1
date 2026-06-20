# Install Insure Chill kiosk. Python can be bundled in runtime\python or installed system-wide.
param(
    [switch]$Offline
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$Monorepo = Split-Path $Root -Parent
$LocalKiosk = $PSScriptRoot
$MonorepoKiosk = Join-Path $Monorepo "scripts\kiosk"
$Kiosk = $MonorepoKiosk
if (
    (Test-Path (Join-Path $LocalKiosk "Resolve-Python.ps1")) -and
    (Test-Path (Join-Path $LocalKiosk "Install-PipDeps.ps1"))
) {
    $Kiosk = $LocalKiosk
}
Set-Location $Root

Write-Host "=== Insure Chill kiosk install ===" -ForegroundColor Cyan
Write-Host "Root: $Root"

. (Join-Path $Kiosk "Resolve-Python.ps1")
. (Join-Path $Kiosk "Install-PipDeps.ps1")
. (Join-Path $PSScriptRoot "Update-EnvDefaults.ps1")

$basePy = Get-KioskPython -Root $Root
$ver = & $basePy -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if (-not $ver) {
    throw "Python executable did not return a version: $basePy"
}
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

if (-not (Test-Path ".env")) {
    Copy-Item $PSScriptRoot\.env.kiosk.example .env
    Write-Host "Created .env from install\.env.kiosk.example" -ForegroundColor Yellow
}
Update-InsureChillEnvDefaults -Root $Root

New-Item -ItemType Directory -Force -Path "$Root\data" | Out-Null

Write-Host ""
Write-Host "Done. Run:" -ForegroundColor Green
Write-Host "  .\run-kiosk.ps1"
Write-Host "  or install\start-insure-chill.cmd"
Write-Host "Screen:  http://127.0.0.1:8768/"
Write-Host "Tablet:  http://127.0.0.1:8768/control"
