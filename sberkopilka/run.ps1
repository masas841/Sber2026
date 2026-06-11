$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& .\.venv\Scripts\Activate.ps1
$env:PIP_DISABLE_PIP_VERSION_CHECK = "1"
python -m pip install -r requirements.txt -q

if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
}

# Освободить порт, если остался старый процесс
$onPort = Get-NetTCPConnection -LocalPort 8766 -State Listen -ErrorAction SilentlyContinue
if ($onPort) {
    $onPort | ForEach-Object {
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 1
}

Write-Host "SberKopilka: http://127.0.0.1:8766  (podklyuchite dzhojstik)" -ForegroundColor Cyan
python -m app.main
