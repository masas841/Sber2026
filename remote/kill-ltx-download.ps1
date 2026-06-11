# Останавливает только python, запущенный для download_ltx_to_d.py (не трогает сервер).
$procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -and $_.CommandLine -match 'download_ltx_to_d' }
foreach ($p in $procs) {
    Write-Host ("Stopping PID {0}: {1}" -f $p.ProcessId, $p.CommandLine)
    Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
if (-not $procs) { Write-Host "No download process found." }
