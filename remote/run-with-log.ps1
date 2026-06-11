# Запуск GIGAvibe с перенаправлением вывода в run.log, чтобы поймать ошибку старта.
$ErrorActionPreference = "SilentlyContinue"
Set-Location C:\Users\user\gigavibe

# Убить старый процесс на 8765, если есть
$conns = Get-NetTCPConnection -LocalPort 8765 -State Listen
foreach ($c in $conns) { Stop-Process -Id $c.OwningProcess -Force }
Start-Sleep -Seconds 1

$env:PATH = "C:\Users\user\gigavibe\.venv\Lib\site-packages\torch\lib;$env:PATH"
$env:PYTHONUNBUFFERED = "1"

$log = "C:\Users\user\gigavibe\run.log"
Remove-Item $log -ErrorAction SilentlyContinue

$p = Start-Process -FilePath "C:\Users\user\gigavibe\.venv\Scripts\python.exe" `
    -ArgumentList "-m", "app.main" `
    -WorkingDirectory "C:\Users\user\gigavibe" `
    -RedirectStandardOutput $log `
    -RedirectStandardError "C:\Users\user\gigavibe\run.err.log" `
    -PassThru -WindowStyle Hidden

Write-Output ("started PID " + $p.Id)
Start-Sleep -Seconds 20

if ($p.HasExited) {
    Write-Output ("PROCESS EXITED with code " + $p.ExitCode)
} else {
    Write-Output "PROCESS STILL RUNNING"
}

Write-Output "--- run.log (tail 30) ---"
Get-Content $log -Tail 30 -ErrorAction SilentlyContinue | Write-Output
Write-Output "--- run.err.log (tail 30) ---"
Get-Content "C:\Users\user\gigavibe\run.err.log" -Tail 30 -ErrorAction SilentlyContinue | Write-Output
