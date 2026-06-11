# Face Landmarker для детекта улыбки (~3 MB) → web/models/
$ErrorActionPreference = "Stop"
$outDir = Join-Path $PSScriptRoot "..\web\models"
$outFile = Join-Path $outDir "face_landmarker.task"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
Write-Host "Downloading $url"
Invoke-WebRequest -Uri $url -OutFile $outFile -UseBasicParsing
$mb = [math]::Round((Get-Item $outFile).Length / 1MB, 2)
Write-Host "OK: $outFile ($mb MB)"
