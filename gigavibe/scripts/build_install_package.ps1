# Build kiosk zip package (portrait only) into dist/.
param(
    [switch]$IncludePython,
    [switch]$Offline,
    [switch]$SkipModels
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

if ($IncludePython -or $Offline) {
    & $Root\scripts\vendor_python.ps1
}

if ($Offline) {
    & $Root\scripts\download_kiosk_wheels.ps1
    if (-not $SkipModels) {
        & $Root\scripts\download_smile_model.ps1
        . (Join-Path $Root "install\Resolve-Python.ps1")
        $py = Get-GigaVenvPython -Root $Root
        if (-not (Test-Path ".venv\Scripts\python.exe")) {
            . (Join-Path $Root "install\Install-Deps.ps1")
            New-GigaVenv -Root $Root -BasePython (Get-GigaPython -Root $Root)
            & .\.venv\Scripts\Activate.ps1
            Install-GigaKioskDeps -Root $Root -WheelsDir (Join-Path $Root "install\wheels")
        }
        & .\.venv\Scripts\Activate.ps1
        python $Root\scripts\download_buffalo_l.py
    }
}

if (Test-Path "$Root\scripts\build_update_manifest.py") {
    $manifestPy = $null
    if (Test-Path "$Root\runtime\python\python.exe") {
        $manifestPy = "$Root\runtime\python\python.exe"
    } else {
        $cmd = Get-Command python -ErrorAction SilentlyContinue
        if ($cmd) { $manifestPy = $cmd.Source }
    }
    if (-not $manifestPy) {
        throw "Python was not found for update manifest generation"
    }
    & $manifestPy "$Root\scripts\build_update_manifest.py"
    if ($LASTEXITCODE -ne 0) { throw "update manifest generation failed" }
}

$distDir = Join-Path $Root "dist"
New-Item -ItemType Directory -Force -Path $distDir | Out-Null

$stamp = Get-Date -Format "yyyyMMdd-HHmm"
$suffix = ""
if ($IncludePython -or $Offline) { $suffix += "-python" }
if ($Offline) { $suffix += "-offline" }
$zipName = "gigavibe-kiosk$suffix-$stamp.zip"
$zipPath = Join-Path $distDir $zipName

$excludeDirs = @(
    ".venv", ".venv-liveportrait", ".git", "dist", "backups",
    "vendor", "models", "tools", "data\outputs", "data\uploads",
    "assets\driving", "assets\video", "__pycache__"
)
$excludeFiles = @("*.pth", "*.onnx", "*.mp4", "*.MP4", "*.safetensors", ".env", "site-packages.zip")

$items = Get-ChildItem -Path $Root -Force | Where-Object {
    $name = $_.Name
    if ($excludeDirs -contains $name) { return $false }
    if (-not $_.PSIsContainer) {
        foreach ($pattern in $excludeFiles) {
            if ($name -like $pattern) { return $false }
        }
    }
    if ($name -match '^\.' -and $name -ne '.env.example') { return $false }
    return $true
}

$staging = Join-Path $env:TEMP "gigavibe-kiosk-$stamp"
if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
New-Item -ItemType Directory -Force -Path $staging | Out-Null

foreach ($item in $items) {
    $dest = Join-Path $staging $item.Name
    if ($item.PSIsContainer) {
        robocopy $item.FullName $dest /E /XD $excludeDirs /XF $excludeFiles /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
    } else {
        Copy-Item $item.FullName $dest -Force
    }
}

$idleVideo = Join-Path $Root "assets\fon.mp4"
if (Test-Path $idleVideo) {
    $idleVideoDest = Join-Path $staging "assets\fon.mp4"
    New-Item -ItemType Directory -Force -Path (Split-Path $idleVideoDest -Parent) | Out-Null
    Copy-Item $idleVideo $idleVideoDest -Force
} else {
    Write-Host "WARN: assets\fon.mp4 is missing; kiosk background video will be unavailable" -ForegroundColor Yellow
}

if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $zipPath -CompressionLevel Optimal
Remove-Item $staging -Recurse -Force

$mb = [math]::Round((Get-Item $zipPath).Length / 1MB, 1)
Write-Host "OK: $zipPath ($mb MB)" -ForegroundColor Green
if ($Offline) {
    Write-Host "On target machine: unzip -> .\install\install.ps1 -Offline -> .env -> .\run-kiosk.ps1"
} elseif ($IncludePython) {
    Write-Host "On target machine: unzip -> .\install\install.ps1 -> .env -> .\run-kiosk.ps1 (Python is bundled)"
} else {
    Write-Host "On target machine: unzip -> .\install\install.ps1 -> .env -> .\run-kiosk.ps1"
}
