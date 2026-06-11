# SB Sans Text Semibold для сцены «Улыбка» → web/fonts/
$ErrorActionPreference = "Stop"
$fontsDir = Join-Path $PSScriptRoot "..\web\fonts"
New-Item -ItemType Directory -Force -Path $fontsDir | Out-Null

$url = "https://db.onlinewebfonts.com/t/cf8ad58acbe94cc96c1196fa2d336b14.woff2"
$out = Join-Path $fontsDir "SBSansText-Semibold.woff2"
Write-Host "GET SBSansText-Semibold.woff2"
Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing
Write-Host "Done: $out ($((Get-Item $out).Length) bytes)"
