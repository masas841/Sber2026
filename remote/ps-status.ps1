Get-CimInstance Win32_Process -Filter "Name='python.exe'" | ForEach-Object {
    $rss = [math]::Round($_.WorkingSetSize/1MB)
    $cl = $_.CommandLine
    Write-Host ("PID {0}  RSS {1} MB  {2}" -f $_.ProcessId, $rss, $cl)
}
