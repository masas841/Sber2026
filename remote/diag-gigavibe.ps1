# Диагностика статуса сервера GIGAvibe на FARM.
$ErrorActionPreference = "SilentlyContinue"

$proc = Get-Process python
if ($proc) {
    Write-Output "PYTHON PROCESSES:"
    $proc | Select-Object Id, StartTime | Format-Table -AutoSize | Out-String | Write-Output
} else {
    Write-Output "NO python process"
}

$listen = Get-NetTCPConnection -LocalPort 8765 -State Listen
if ($listen) {
    Write-Output ("LISTENING 8765 by PID " + ($listen.OwningProcess -join ","))
} else {
    Write-Output "NOT LISTENING on 8765"
}

$log = "C:\Users\user\gigavibe\server.log"
if (Test-Path $log) {
    Write-Output ("log mtime: " + (Get-Item $log).LastWriteTime)
    Write-Output "--- log tail (12) ---"
    Get-Content $log -Tail 12 | Write-Output
}
