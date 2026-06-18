# Build kiosk zip package into dist/.
param(
    [switch]$IncludePython,
    [switch]$Offline
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$Monorepo = Split-Path $Root -Parent

$offlineHook = $null
if ($Offline) {
    $offlineHook = {
        & (Join-Path $Root "scripts\download_mediapipe_tasks_vision.ps1")
        & (Join-Path $Root "scripts\download_smile_model.ps1")
    }
}

& (Join-Path $Monorepo "scripts\kiosk\build_install_package.ps1") `
    -ProjectRoot $Root `
    -PackageName "smile-pay-kiosk" `
    -RepoSubdir "smile-pay" `
    -ExcludeDirs @("data") `
    -ExcludeParts @("scripts/figma_out") `
    -IncludePython:$IncludePython `
    -Offline:$Offline `
    -OfflineAssetsHook $offlineHook
