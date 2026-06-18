param(
    [switch]$UpdateFromGitHub,
    [switch]$SkipUpdate
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Read-DotEnvValue {
    param(
        [string]$Path,
        [string]$Name
    )

    if (-not (Test-Path $Path)) { return $null }
    $pattern = "^\s*$([regex]::Escape($Name))\s*=\s*(.*)\s*$"
    foreach ($line in Get-Content -Path $Path) {
        if ($line -match "^\s*#") { continue }
        if ($line -match $pattern) {
            return $matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return $null
}

function Test-DotEnvBool {
    param(
        [string]$Path,
        [string]$Name
    )

    $value = Read-DotEnvValue -Path $Path -Name $Name
    if (-not $value) { return $false }
    return $value -match "^(1|true|yes|on)$"
}

$envPath = Join-Path $PSScriptRoot ".env"
$autoUpdate = Test-DotEnvBool -Path $envPath -Name "AUTO_UPDATE_FROM_GITHUB"
if (-not $SkipUpdate -and ($UpdateFromGitHub -or $autoUpdate)) {
    $updater = Join-Path $PSScriptRoot "install\update-from-github.ps1"
    if (Test-Path $updater) {
        Write-Host "[SmilePay] Checking GitHub update ..." -ForegroundColor Cyan
        & $updater
    }
}

$Monorepo = Split-Path $PSScriptRoot -Parent
. (Join-Path $Monorepo "scripts\kiosk\Resolve-Python.ps1")
. (Join-Path $Monorepo "scripts\kiosk\Install-PipDeps.ps1")

$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    $basePy = Get-KioskPython -Root $PSScriptRoot
    Write-Host "[SmilePay] Creating .venv from $basePy ..."
    New-KioskVenv -Root $PSScriptRoot -BasePython $basePy
    & .\.venv\Scripts\Activate.ps1
    Install-KioskPipDeps -Root $PSScriptRoot
} else {
    & .\.venv\Scripts\Activate.ps1
}

if (-not (Test-Path ".env")) {
    if (Test-Path "install\.env.kiosk.example") {
        Copy-Item "install\.env.kiosk.example" ".env"
    }
}

$envDefaults = Join-Path $PSScriptRoot "install\Update-EnvDefaults.ps1"
if (Test-Path $envDefaults) {
    . $envDefaults
    Invoke-SmilePayPostUpdateHooks -Root $PSScriptRoot
}

$port = Read-DotEnvValue -Path $envPath -Name "PORT"
if (-not $port) { $port = "8888" }

Write-Host "Smile Pay: http://127.0.0.1:$port" -ForegroundColor Cyan
Write-Host "Preview:   http://127.0.0.1:$port/?stage=intro" -ForegroundColor DarkCyan
python -m app.main
