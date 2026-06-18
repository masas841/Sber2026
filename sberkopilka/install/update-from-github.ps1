param(
    [switch]$DryRun,
    [switch]$FullArchive,
    [switch]$KeepTemp
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$Monorepo = Split-Path $Root -Parent

. (Join-Path $Monorepo "scripts\kiosk\Update-FromGitHub.ps1")
. (Join-Path $PSScriptRoot "Update-EnvDefaults.ps1")

Invoke-KioskGitHubUpdate -AppLabel "SberKopilka" -Root $Root -Subdir "sberkopilka" `
    -DryRun:$DryRun -FullArchive:$FullArchive -KeepTemp:$KeepTemp `
    -PostUpdateHook { Update-SberKopilkaEnvDefaults -Root $Root }
