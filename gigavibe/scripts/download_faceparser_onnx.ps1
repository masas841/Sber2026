# faceparser_resnet34.onnx (BiSeNet face parsing, VisoMaster assets)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Out = Join-Path $Root "models\faceparser\faceparser_resnet34.onnx"
New-Item -ItemType Directory -Force -Path (Split-Path $Out) | Out-Null
$Url = "https://github.com/visomaster/visomaster-assets/releases/download/v0.1.0/faceparser_resnet34.onnx"
Write-Host "Downloading $Url -> $Out"
Invoke-WebRequest -Uri $Url -OutFile $Out -UseBasicParsing
$mb = [math]::Round((Get-Item $Out).Length / 1MB, 1)
Write-Host "Done: $mb MB"
