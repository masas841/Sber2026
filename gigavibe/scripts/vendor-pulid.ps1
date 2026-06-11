# vendor/pulid — git clone https://github.com/ToTheBeginning/PuLID
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$dest = Join-Path $root "vendor\pulid"
if (Test-Path (Join-Path $dest ".git")) {
    Write-Host "OK vendor/pulid exists"
    exit 0
}
git clone --depth 1 https://github.com/ToTheBeginning/PuLID.git $dest
Write-Host "OK vendor/pulid ready: $dest"
