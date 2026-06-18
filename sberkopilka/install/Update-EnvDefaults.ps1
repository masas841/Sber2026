function Read-KioskDotEnvValue {
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

function Add-KioskEnvDefault {
    param(
        [string]$Path,
        [string]$Name,
        [string]$Value,
        [string]$Comment = ""
    )

    $existing = Read-KioskDotEnvValue -Path $Path -Name $Name
    if ($null -ne $existing) { return $false }
    if ($Comment) {
        Add-Content -Path $Path -Value $Comment -Encoding UTF8
    }
    Add-Content -Path $Path -Value "$Name=$Value" -Encoding UTF8
    return $true
}

function Update-SberKopilkaEnvDefaults {
    param([string]$Root)

    $envFile = Join-Path $Root ".env"
    $example = Join-Path $Root "install\.env.kiosk.example"
    if (-not (Test-Path $envFile)) {
        if (Test-Path $example) {
            Copy-Item $example $envFile
            Write-Host "[SberKopilka] Created .env from install\.env.kiosk.example" -ForegroundColor Yellow
        } else {
            New-Item -ItemType File -Path $envFile -Force | Out-Null
        }
    }

    $added = 0
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "PLAY_LOG_FILE" -Value "data/plays.jsonl" -Comment "# Persistent play log for daily stats.")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "PLAY_LOG_TZ" -Value "Europe/Moscow")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "AUTO_UPDATE_FROM_GITHUB" -Value "false" -Comment "# Updater: pull latest app files from GitHub before launch.")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "UPDATE_REPO_REF" -Value "main")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "UPDATE_MANIFEST_URL" -Value "https://raw.githubusercontent.com/masas841/Sber2026/main/sberkopilka/install/update-manifest.json")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "UPDATE_RAW_BASE_URL" -Value "https://raw.githubusercontent.com/masas841/Sber2026/main/sberkopilka")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "UPDATE_REPO_ARCHIVE_URL" -Value "https://github.com/masas841/Sber2026/archive/refs/heads/main.zip")

    if ($added -gt 0) {
        Write-Host "[SberKopilka] .env migration: added $added setting(s)." -ForegroundColor Green
    }
}
