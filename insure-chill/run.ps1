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

$onPort = Get-NetTCPConnection -LocalPort 8768 -State Listen -ErrorAction SilentlyContinue
if ($onPort) {
    $onPort | ForEach-Object {
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 1
}

Write-Host "Insure Chill screen:  http://127.0.0.1:8768/" -ForegroundColor Cyan
Write-Host "Insure Chill tablet:  http://127.0.0.1:8768/control" -ForegroundColor Cyan
python -m app.main
