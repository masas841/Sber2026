$conns = Get-NetTCPConnection -LocalPort 8768 -State Listen -ErrorAction SilentlyContinue
foreach ($c in $conns) {
    Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2
schtasks /Run /TN InsureChill | Out-Null
