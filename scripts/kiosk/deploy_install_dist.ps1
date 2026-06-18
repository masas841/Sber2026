# Upload latest kiosk install zip to farm dist/ for /install endpoint.
param(
    [Parameter(Mandatory = $true)]
    [string]$Farm,
    [Parameter(Mandatory = $true)]
    [string]$LocalRoot,
    [Parameter(Mandatory = $true)]
    [string]$RemoteRoot,
    [string]$PackageName = ""
)

$ErrorActionPreference = "Stop"
$distDir = Join-Path $LocalRoot "dist"
if (-not (Test-Path $distDir)) {
    Write-Host "WARN: dist/ missing — skip install package upload" -ForegroundColor Yellow
    return
}

$pattern = if ($PackageName) { "$PackageName*.zip" } else { "*-kiosk*.zip" }
$latest = Get-ChildItem -Path $distDir -Filter $pattern -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $latest) {
    Write-Host "WARN: no install package in $distDir — run scripts\build_install_package.ps1" -ForegroundColor Yellow
    return
}

$remoteDist = ($RemoteRoot -replace "\\", "/") + "/dist"
& ssh $Farm "if not exist `"$($RemoteRoot -replace '/','\\')\dist`" mkdir `"$($RemoteRoot -replace '/','\\')\dist`""
if ($LASTEXITCODE -ne 0) { throw "ssh mkdir dist failed" }

Write-Host "=== Upload install package: $($latest.Name) ($([math]::Round($latest.Length / 1MB, 1)) MB) ===" -ForegroundColor Cyan
& scp $latest.FullName "${Farm}:${remoteDist}/"
if ($LASTEXITCODE -ne 0) { throw "scp install package failed" }

$installReadme = Join-Path $LocalRoot "install\README-INSTALL.md"
if (Test-Path $installReadme) {
    $remoteInstall = ($RemoteRoot -replace "\\", "/") + "/install"
    & ssh $Farm "if not exist `"$($RemoteRoot -replace '/','\\')\install`" mkdir `"$($RemoteRoot -replace '/','\\')\install`""
    & scp $installReadme "${Farm}:${remoteInstall}/README-INSTALL.md"
    if ($LASTEXITCODE -ne 0) { throw "scp README-INSTALL.md failed" }
}

Write-Host "Install URL: /install/ (package: $($latest.Name))" -ForegroundColor Green
