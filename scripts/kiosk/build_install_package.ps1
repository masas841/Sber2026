# Build kiosk zip package into dist/.
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot,
    [Parameter(Mandatory = $true)]
    [string]$PackageName,
    [Parameter(Mandatory = $true)]
    [string]$RepoSubdir,
    [string[]]$ExcludeDirs = @(),
    [string[]]$ExcludeParts = @(),
    [string[]]$ExcludeFiles = @(),
    [string]$RequirementsFile = "requirements.txt",
    [switch]$IncludePython,
    [switch]$Offline,
    [scriptblock]$OfflineAssetsHook
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path $ProjectRoot).Path
$Monorepo = Split-Path $Root -Parent
$KioskScripts = Join-Path $Monorepo "scripts\kiosk"
Set-Location $Root

if ($IncludePython -or $Offline) {
    & (Join-Path $KioskScripts "vendor_python.ps1") -Root $Root
}

if ($Offline) {
    & (Join-Path $KioskScripts "download_wheels.ps1") -Root $Root -RequirementsFile $RequirementsFile
    if ($OfflineAssetsHook) {
        & $OfflineAssetsHook
    }
}

$manifestPy = Join-Path $KioskScripts "build_update_manifest.py"
$manifestArgs = @(
    $manifestPy,
    "--root", $Root,
    "--name", $RepoSubdir
)
foreach ($part in $ExcludeParts) {
    $manifestArgs += "--exclude-part"
    $manifestArgs += ($part -replace "\\", "/")
}
$manifestRunner = $null
if (Test-Path (Join-Path $Root "runtime\python\python.exe")) {
    $manifestRunner = Join-Path $Root "runtime\python\python.exe"
} else {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $manifestRunner = $cmd.Source }
}
if (-not $manifestRunner) {
    throw "Python was not found for update manifest generation"
}
& $manifestRunner @manifestArgs
if ($LASTEXITCODE -ne 0) { throw "update manifest generation failed" }

$distDir = Join-Path $Root "dist"
New-Item -ItemType Directory -Force -Path $distDir | Out-Null

$stamp = Get-Date -Format "yyyyMMdd-HHmm"
$suffix = ""
if ($IncludePython -or $Offline) { $suffix += "-python" }
if ($Offline) { $suffix += "-offline" }
$zipName = "$PackageName$suffix-$stamp.zip"
$zipPath = Join-Path $distDir $zipName

$baseExcludeDirs = @(
    ".venv", ".git", "dist", "backups", "__pycache__"
) + $ExcludeDirs
$baseExcludeFiles = @(".env", "*.pyc", "*.pyo", "*.log") + $ExcludeFiles

$items = Get-ChildItem -Path $Root -Force | Where-Object {
    $name = $_.Name
    if ($baseExcludeDirs -contains $name) { return $false }
    if (-not $_.PSIsContainer) {
        foreach ($pattern in $baseExcludeFiles) {
            if ($name -like $pattern) { return $false }
        }
    }
    if ($name -match '^\.' -and $name -ne '.env.example') { return $false }
    return $true
}

$staging = Join-Path $env:TEMP "$PackageName-$stamp"
if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
New-Item -ItemType Directory -Force -Path $staging | Out-Null

foreach ($item in $items) {
    $dest = Join-Path $staging $item.Name
    if ($item.PSIsContainer) {
        robocopy $item.FullName $dest /E /XD $baseExcludeDirs /XF $baseExcludeFiles /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
    } else {
        Copy-Item $item.FullName $dest -Force
    }
}

if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $zipPath -CompressionLevel Optimal
Remove-Item $staging -Recurse -Force

$mb = [math]::Round((Get-Item $zipPath).Length / 1MB, 1)
$latestPath = Join-Path $distDir "$PackageName-latest.zip"
Copy-Item $zipPath $latestPath -Force
Write-Host "OK: $zipPath ($mb MB)" -ForegroundColor Green
Write-Host "Latest: $latestPath" -ForegroundColor Green
Write-Host "On target machine: unzip -> .\install\install.ps1$(if ($Offline) { ' -Offline' }) -> .env -> .\run-kiosk.ps1"
