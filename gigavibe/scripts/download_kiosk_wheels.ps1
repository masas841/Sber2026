# Кэш pip-колёс для офлайн-установки киоска (запускать на машине с интернетом)
param(
    [string]$WheelsDir = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

if (-not $WheelsDir) {
    $WheelsDir = Join-Path $Root "install\wheels"
}
New-Item -ItemType Directory -Force -Path $WheelsDir | Out-Null

. (Join-Path $Root "install\Resolve-Python.ps1")
$basePy = Get-GigaPython -Root $Root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    . (Join-Path $Root "install\Install-Deps.ps1")
    New-GigaVenv -Root $Root -BasePython $basePy
}
& .\.venv\Scripts\Activate.ps1

$pkgs = @(
    "numpy>=1.24.4,<2",
    "sympy==1.13.1",
    "-r", "requirements-kiosk.txt",
    "onnxruntime-gpu==1.19.2",
    "coloredlogs", "flatbuffers", "packaging", "protobuf",
    "insightface>=0.7.3",
    "onnx", "tqdm", "easydict", "prettytable",
    "scikit-image", "scikit-learn", "matplotlib"
)

Write-Host "Downloading wheels to $WheelsDir …"
python -m pip download -c constraints.txt -d $WheelsDir @pkgs
if ($LASTEXITCODE -ne 0) { throw "pip download failed" }

$count = (Get-ChildItem $WheelsDir -Filter "*.whl").Count
$mb = [math]::Round((Get-ChildItem $WheelsDir | Measure-Object Length -Sum).Sum / 1MB, 1)
Write-Host "OK: $count wheels ($mb MB) in $WheelsDir" -ForegroundColor Green
