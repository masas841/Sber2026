# MediaPipe tasks-vision JS + WASM for offline kiosk (no jsdelivr at runtime)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

$version = "0.10.14"
$baseUrl = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@$version"
$outRoot = Join-Path $PSScriptRoot "..\web\vendor\mediapipe\tasks-vision"
New-Item -ItemType Directory -Force -Path (Join-Path $outRoot "wasm") | Out-Null

$files = @(
    "vision_bundle.mjs",
    "wasm/vision_wasm_internal.js",
    "wasm/vision_wasm_internal.wasm",
    "wasm/vision_wasm_nosimd_internal.js",
    "wasm/vision_wasm_nosimd_internal.wasm"
)

foreach ($rel in $files) {
    $dest = Join-Path $outRoot ($rel -replace "/", [IO.Path]::DirectorySeparatorChar)
    $dir = Split-Path $dest -Parent
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
    if (Test-Path $dest) {
        Write-Host "OK (exists): $rel"
        continue
    }
    $url = "$baseUrl/$($rel -replace '\\','/')"
    Write-Host "Downloading $url"
    Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
    $kb = [math]::Round((Get-Item $dest).Length / 1KB, 1)
    Write-Host "  -> $dest ($kb KB)"
}

Write-Host "MediaPipe tasks-vision $version ready under web\vendor\mediapipe\tasks-vision"
