Get-PSDrive -PSProvider FileSystem | ForEach-Object {
    $free = [math]::Round($_.Free/1GB,1)
    $used = [math]::Round($_.Used/1GB,1)
    Write-Host ("{0}: free={1} GB, used={2} GB" -f $_.Name, $free, $used)
}
