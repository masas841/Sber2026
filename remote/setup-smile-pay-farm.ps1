# First-time / update setup on FARM: venv, deps, .env, firewall, scheduled task.
$ErrorActionPreference = "Stop"

$proj = "C:\Users\user\smile-pay"
$remote = Join-Path $proj "remote"
Set-Location $proj

New-Item -ItemType Directory -Path $remote -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $proj "data") -Force | Out-Null

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[setup] Creating venv..."
    python -m venv .venv
}

Write-Host "[setup] pip install..."
& .\.venv\Scripts\python.exe -m pip install -q --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt

$neighborCert = "C:\Users\user\gigavibe\certs\cert.pem"
$neighborKey = "C:\Users\user\gigavibe\certs\key.pem"
if ((Test-Path $neighborCert) -and (Test-Path $neighborKey)) {
    Write-Host "[setup] Reusing Let's Encrypt cert from GIGAvibe..."
    New-Item -ItemType Directory -Path "certs" -Force | Out-Null
    Copy-Item $neighborCert "certs\cert.pem" -Force
    Copy-Item $neighborKey "certs\key.pem" -Force
} elseif (-not (Test-Path "certs\cert.pem") -or -not (Test-Path "certs\key.pem")) {
    Write-Host "[setup] Generating self-signed TLS cert..."
    & .\.venv\Scripts\python.exe -m scripts.gen_self_signed_cert 192.168.1.243 slash.omelchak.com
}

$envSrc = Join-Path $remote "farm-smile-pay.env"
if (Test-Path $envSrc) {
    Copy-Item $envSrc (Join-Path $proj ".env") -Force
    Write-Host "[setup] .env from farm-smile-pay.env"
}

& netsh advfirewall firewall delete rule name=SmilePay-8767 2>&1 | Out-Null
& netsh advfirewall firewall add rule name=SmilePay-8767 dir=in action=allow protocol=TCP localport=8767 | Out-Null
Write-Host "[setup] Firewall rule for TCP 8767"

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $remote "register-smile-pay-task.ps1")
Write-Host "[setup] Done."
