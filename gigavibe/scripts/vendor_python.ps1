# Portable Python in runtime\python (embeddable + pip + virtualenv).
param(
    [string]$Version = "3.12.8",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$Target = Join-Path $Root "runtime\python"
$Marker = Join-Path $Target "python.exe"

if ((Test-Path $Marker) -and -not $Force) {
    $v = & $Marker -c "import sys; print(sys.version.split()[0])"
    Write-Host "Python already exists: $Marker ($v)" -ForegroundColor Green
    return
}

$cacheDir = Join-Path $Root "dist\cache"
New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null

$zipName = "python-$Version-embed-amd64.zip"
$zipUrl = "https://www.python.org/ftp/python/$Version/$zipName"
$zipPath = Join-Path $cacheDir $zipName

if (-not (Test-Path $zipPath)) {
    Write-Host "Downloading $zipUrl"
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
}

if (Test-Path $Target) {
    Remove-Item $Target -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $Target | Out-Null
Expand-Archive -Path $zipPath -DestinationPath $Target -Force

$parts = $Version.Split(".")
$majMin = "$($parts[0])$($parts[1])"
$pthFile = Join-Path $Target "python$majMin._pth"
if (-not (Test-Path $pthFile)) {
    throw "File not found: $pthFile"
}

@(
    "python$majMin.zip",
    ".",
    "Lib\site-packages",
    "import site"
) | Set-Content -Path $pthFile -Encoding ASCII

New-Item -ItemType Directory -Force -Path (Join-Path $Target "Lib\site-packages") | Out-Null

$getPip = Join-Path $cacheDir "get-pip.py"
if (-not (Test-Path $getPip)) {
    Write-Host "Downloading get-pip.py"
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPip -UseBasicParsing
}

Write-Host "Installing pip ..."
& $Marker $getPip --no-warn-script-location -q
if ($LASTEXITCODE -ne 0) { throw "get-pip failed" }

Write-Host "Installing virtualenv ..."
& $Marker -m pip install virtualenv -q
if ($LASTEXITCODE -ne 0) { throw "virtualenv install failed" }

$ver = & $Marker -c "import sys; print(sys.version)"
Write-Host "OK: $Marker" -ForegroundColor Green
Write-Host $ver
