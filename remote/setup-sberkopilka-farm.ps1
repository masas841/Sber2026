# First-time / update setup on FARM: venv, deps, .env, firewall, scheduled task.
$ErrorActionPreference = "Stop"

$proj = "C:\Users\user\sberkopilka"
$remote = Join-Path $proj "remote"
Set-Location $proj

New-Item -ItemType Directory -Path (Join-Path $proj "data") -Force | Out-Null
New-Item -ItemType Directory -Path $remote -Force | Out-Null

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[setup] Creating venv..."
    python -m venv .venv
}

Write-Host "[setup] pip install..."
& .\.venv\Scripts\python.exe -m pip install -q --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt

$envSrc = Join-Path $remote "farm-sberkopilka.env"
if (-not (Test-Path $envSrc)) {
    throw "Missing $envSrc"
}
Copy-Item $envSrc (Join-Path $proj ".env") -Force
Write-Host "[setup] .env from farm-sberkopilka.env"

& netsh advfirewall firewall delete rule name=SberKopilka-8766 2>&1 | Out-Null
& netsh advfirewall firewall add rule name=SberKopilka-8766 dir=in action=allow protocol=TCP localport=8766 | Out-Null
Write-Host "[setup] Firewall rule for TCP 8766"

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $remote "register-sberkopilka-task.ps1")
Write-Host "[setup] Done."
