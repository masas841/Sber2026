# enable-https.ps1 — включить HTTPS в .env и перезапустить GIGAvibe
$ErrorActionPreference = "Continue"
$proj = "C:\Users\user\gigavibe"
$envFile = Join-Path $proj ".env"

$lines = Get-Content $envFile -ErrorAction SilentlyContinue | Where-Object {
    $_ -notmatch '^\s*(USE_HTTPS|SSL_CERTFILE|SSL_KEYFILE)\s*='
}
$lines += @(
    "USE_HTTPS=true",
    "SSL_CERTFILE=certs/cert.pem",
    "SSL_KEYFILE=certs/key.pem"
)
Set-Content -Path $envFile -Value $lines -Encoding ascii
Write-Host ".env updated: USE_HTTPS=true"

# restart
$conns = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
foreach ($c in $conns) {
    Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2
schtasks /Run /TN GIGAvibe 2>&1 | Out-Null
Write-Host "GIGAvibe task restarted."
