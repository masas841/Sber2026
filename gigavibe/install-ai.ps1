$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# CUDA 12.4 wheels for RTX 3060 Ti.
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124

Write-Host "Done. Run: .\run.ps1"
