# Build kiosk zip package into dist/.
param(
    [switch]$WithoutPython,
    [switch]$Offline
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$Monorepo = Split-Path $Root -Parent
$includePython = -not $WithoutPython

& (Join-Path $Monorepo "scripts\kiosk\build_install_package.ps1") `
    -ProjectRoot $Root `
    -PackageName "insure-chill-kiosk" `
    -RepoSubdir "insure-chill" `
    -ExcludeDirs @("data") `
    -ExcludeParts @(
        "static/assets/figma/threats/_context",
        "static/assets/figma/control/_context"
    ) `
    -IncludePython:$includePython `
    -Offline:$Offline
