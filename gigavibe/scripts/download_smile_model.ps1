# Face Landmarker model for kiosk smile capture (~3 MB)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

$outDir = Join-Path $PSScriptRoot "..\web\models"  # /static/models/ — mount web → /static
$outFile = Join-Path $outDir "face_landmarker.task"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
Write-Host "Downloading $url"
Invoke-WebRequest -Uri $url -OutFile $outFile -UseBasicParsing
$mb = [math]::Round((Get-Item $outFile).Length / 1MB, 2)
Write-Host "OK: $outFile ($mb MB)"
Write-Host "Kiosk will use /static/models/face_landmarker.task (no Google CDN at runtime)"
