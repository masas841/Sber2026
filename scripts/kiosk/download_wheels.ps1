# Cache pip wheels for offline kiosk installation. Run on a machine with internet access.
param(
    [Parameter(Mandatory = $true)]
    [string]$Root,
    [string]$WheelsDir = "",
    [string]$RequirementsFile = "requirements.txt"
)

$ErrorActionPreference = "Stop"
Set-Location $Root

if (-not $WheelsDir) {
    $WheelsDir = Join-Path $Root "install\wheels"
}
New-Item -ItemType Directory -Force -Path $WheelsDir | Out-Null

$kioskScripts = Join-Path (Split-Path $Root -Parent) "scripts\kiosk"
. (Join-Path $kioskScripts "Resolve-Python.ps1")
. (Join-Path $kioskScripts "Install-PipDeps.ps1")

$basePy = Get-KioskPython -Root $Root
$reqPath = Join-Path $Root $RequirementsFile
if (-not (Test-Path $reqPath)) {
    throw "Requirements file not found: $reqPath"
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    New-KioskVenv -Root $Root -BasePython $basePy
}
& .\.venv\Scripts\Activate.ps1

Write-Host "Downloading wheels to $WheelsDir ..."
python -m pip download -d $WheelsDir -r $reqPath
if ($LASTEXITCODE -ne 0) { throw "pip download failed" }

$count = (Get-ChildItem $WheelsDir -Filter "*.whl").Count
$mb = [math]::Round((Get-ChildItem $WheelsDir | Measure-Object Length -Sum).Sum / 1MB, 1)
Write-Host "OK: $count wheels ($mb MB) in $WheelsDir" -ForegroundColor Green
