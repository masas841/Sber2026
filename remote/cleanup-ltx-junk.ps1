# Удаляет лишние файлы LTX (корневые чекпойнты, media), оставляя diffusers-подпапки.
$dir = "D:\gigavibe-models\LTX-Video"
if (-not (Test-Path $dir)) { Write-Host "no dir"; exit 0 }

$before = (Get-ChildItem $dir -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
Get-ChildItem $dir -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like 'ltx-video-*' -or $_.Name -like 'ltxv-13b-*' } |
    ForEach-Object { Write-Host ("del " + $_.Name); Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue }
if (Test-Path (Join-Path $dir "media")) {
    Remove-Item (Join-Path $dir "media") -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "del media/"
}
$after = (Get-ChildItem $dir -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
Write-Host ("freed_GB=" + [math]::Round(($before - $after)/1GB,1))
Write-Host ("remaining_GB=" + [math]::Round($after/1GB,1))
