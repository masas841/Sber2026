$ErrorActionPreference = "Stop"
$dest = "C:\Users\user\ffmpeg"
$exe  = Join-Path $dest "ffmpeg.exe"
if (Test-Path $exe) {
    Write-Host "ALREADY_INSTALLED $exe"
    & $exe -version | Select-Object -First 1
    exit 0
}
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$zip = Join-Path $env:TEMP "ffmpeg-essentials.zip"
$url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
Write-Host "Downloading $url"
curl.exe -L -o $zip $url
Write-Host "Extracting..."
$tmp = Join-Path $env:TEMP "ffmpeg-extract"
if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
tar -xf $zip -C $tmp
$bin = Get-ChildItem -Path $tmp -Recurse -Filter ffmpeg.exe | Select-Object -First 1
if (-not $bin) { throw "ffmpeg.exe not found after extract" }
Copy-Item $bin.FullName $exe -Force
$probe = Join-Path (Split-Path $bin.FullName) "ffprobe.exe"
if (Test-Path $probe) { Copy-Item $probe (Join-Path $dest "ffprobe.exe") -Force }
Remove-Item -Recurse -Force $tmp
Remove-Item -Force $zip
Write-Host "INSTALLED $exe"
& $exe -version | Select-Object -First 1
