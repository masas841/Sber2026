$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& .\.venv\Scripts\Activate.ps1
python -m pip install -q -r requirements.txt

$env:PORT = if ($env:PORT) { $env:PORT } else { "8888" }
Write-Host "Smile Pay: http://127.0.0.1:$env:PORT" -ForegroundColor Cyan
Write-Host "Preview:   http://127.0.0.1:$env:PORT/?stage=intro" -ForegroundColor DarkCyan
python -m app.main
