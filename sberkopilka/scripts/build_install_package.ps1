# Build kiosk zip package into dist/.
param(
    [switch]$IncludePython,
    [switch]$Offline
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$Monorepo = Split-Path $Root -Parent

& (Join-Path $Monorepo "scripts\kiosk\build_install_package.ps1") `
    -ProjectRoot $Root `
    -PackageName "sberkopilka-kiosk" `
    -RepoSubdir "sberkopilka" `
    -ExcludeDirs @("data") `
    -ExcludeParts @("web/assets/figma/_context") `
    -IncludePython:$IncludePython `
    -Offline:$Offline
