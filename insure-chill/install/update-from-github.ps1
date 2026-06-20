param(
    [switch]$DryRun,
    [switch]$FullArchive,
    [switch]$KeepTemp
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$Monorepo = Split-Path $Root -Parent
$LocalUpdater = Join-Path $PSScriptRoot "Update-FromGitHub.ps1"
$MonorepoUpdater = Join-Path $Monorepo "scripts\kiosk\Update-FromGitHub.ps1"
$Updater = $MonorepoUpdater
if (Test-Path $LocalUpdater) {
    $Updater = $LocalUpdater
}

. $Updater
. (Join-Path $PSScriptRoot "Update-EnvDefaults.ps1")

Invoke-KioskGitHubUpdate -AppLabel "InsureChill" -Root $Root -Subdir "insure-chill" `
    -DryRun:$DryRun -FullArchive:$FullArchive -KeepTemp:$KeepTemp `
    -PostUpdateHook { Update-InsureChillEnvDefaults -Root $Root }
