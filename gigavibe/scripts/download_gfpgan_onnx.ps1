# GFPGANv1.4.onnx (VisoMaster / Rope assets)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Out = Join-Path $Root "models\gfpgan\GFPGANv1.4.onnx"
New-Item -ItemType Directory -Force -Path (Split-Path $Out) | Out-Null
$Url = "https://github.com/visomaster/visomaster-assets/releases/download/v0.1.0/GFPGANv1.4.onnx"
Write-Host "Downloading $Url -> $Out"
Invoke-WebRequest -Uri $Url -OutFile $Out -UseBasicParsing
$mb = [math]::Round((Get-Item $Out).Length / 1MB, 1)
Write-Host "Done: $mb MB"
