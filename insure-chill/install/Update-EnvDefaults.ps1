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

function Add-KioskEnvListItem {
    param(
        [string]$Path,
        [string]$Name,
        [string]$Item
    )

    if (-not (Test-Path $Path)) { return $false }
    $lines = @(Get-Content -Path $Path)
    $pattern = "^\s*$([regex]::Escape($Name))\s*=\s*(.*)\s*$"
    for ($idx = 0; $idx -lt $lines.Count; $idx++) {
        $line = $lines[$idx]
        if ($line -match "^\s*#") { continue }
        if ($line -match $pattern) {
            $value = $matches[1].Trim().Trim('"').Trim("'")
            $items = @($value -split "[;,]" | ForEach-Object { $_.Trim() } | Where-Object { $_ })
            if ($items -contains $Item) { return $false }
            $sep = ";"
            $lines[$idx] = "$Name=$value$sep$Item"
            Set-Content -Path $Path -Value $lines -Encoding UTF8
            return $true
        }
    }
    return $false
}

function Update-InsureChillEnvDefaults {
    param([string]$Root)

    $envFile = Join-Path $Root ".env"
    $example = Join-Path $Root "install\.env.kiosk.example"
    if (-not (Test-Path $envFile)) {
        if (Test-Path $example) {
            Copy-Item $example $envFile
            Write-Host "[InsureChill] Created .env from install\.env.kiosk.example" -ForegroundColor Yellow
        } else {
            New-Item -ItemType File -Path $envFile -Force | Out-Null
        }
    }

    $added = 0
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "PLAY_LOG_FILE" -Value "data/plays.jsonl" -Comment "# Persistent play log for daily stats.")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "PLAY_LOG_TZ" -Value "Europe/Moscow")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "LOG_UPLOAD_ENABLED" -Value "true" -Comment "# Realtime diagnostics: send kiosk logs to photo_receiver.")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "LOG_UPLOAD_URL" -Value "https://sberfest2026.ru" -Comment "# Diagnostics: upload kiosk logs to photo_receiver.")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "LOG_UPLOAD_API_KEY" -Value "")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "LOG_UPLOAD_AUTH" -Value "bearer")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "LOG_UPLOAD_KIOSK_ID" -Value $env:COMPUTERNAME)
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "LOG_UPLOAD_INTERVAL_SEC" -Value "60")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "LOG_UPLOAD_PATHS" -Value "data/srv_out.log;data/srv_err.log;server.log;data/plays.jsonl;data/games.jsonl")
    $added += [int](Add-KioskEnvListItem -Path $envFile -Name "LOG_UPLOAD_PATHS" -Item "data/games.jsonl")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "LOG_UPLOAD_MAX_BYTES" -Value "524288")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "LOG_UPLOAD_INITIAL_TAIL_BYTES" -Value "262144")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "AUTO_UPDATE_FROM_GITHUB" -Value "false" -Comment "# Updater: pull latest app files from GitHub before launch.")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "UPDATE_REPO_REF" -Value "main")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "UPDATE_MANIFEST_URL" -Value "https://raw.githubusercontent.com/masas841/Sber2026/main/insure-chill/install/update-manifest.json")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "UPDATE_RAW_BASE_URL" -Value "https://raw.githubusercontent.com/masas841/Sber2026/main/insure-chill")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "UPDATE_REPO_ARCHIVE_URL" -Value "https://github.com/masas841/Sber2026/archive/refs/heads/main.zip")

    if ($added -gt 0) {
        Write-Host "[InsureChill] .env migration: added $added setting(s)." -ForegroundColor Green
    }
}
