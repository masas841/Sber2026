function Read-GigaDotEnvValue {
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

function Add-GigaEnvDefault {
    param(
        [string]$Path,
        [string]$Name,
        [string]$Value,
        [string]$Comment = ""
    )

    $existing = Read-GigaDotEnvValue -Path $Path -Name $Name
    if ($null -ne $existing) { return $false }
    if ($Comment) {
        Add-Content -Path $Path -Value $Comment -Encoding UTF8
    }
    Add-Content -Path $Path -Value "$Name=$Value" -Encoding UTF8
    return $true
}

function Ensure-GigaMediaPipeVendor {
    param([string]$Root)

    $bundle = Join-Path $Root "web\vendor\mediapipe\tasks-vision\vision_bundle.mjs"
    if (Test-Path $bundle) { return }
    $script = Join-Path $Root "scripts\download_mediapipe_tasks_vision.ps1"
    if (-not (Test-Path $script)) {
        Write-Host "WARN: MediaPipe vendor missing and download script not found" -ForegroundColor Yellow
        return
    }
    Write-Host "[GIGAvibe] Downloading local MediaPipe tasks-vision (offline WASM)..." -ForegroundColor Yellow
    & $script
}

function Update-GigaEnvDefaults {
    param([string]$Root)

    $envFile = Join-Path $Root ".env"
    $example = Join-Path $Root "install\.env.kiosk.example"
    if (-not (Test-Path $envFile)) {
        if (Test-Path $example) {
            Copy-Item $example $envFile
            Write-Host "[GIGAvibe] Created .env from install\.env.kiosk.example" -ForegroundColor Yellow
        } else {
            New-Item -ItemType File -Path $envFile -Force | Out-Null
            Write-Host "[GIGAvibe] Created empty .env" -ForegroundColor Yellow
        }
    }

    $added = 0
    $added += [int](Add-GigaEnvDefault -Path $envFile -Name "LOG_UPLOAD_ENABLED" -Value "true" -Comment "# Realtime diagnostics: send kiosk logs to photo_receiver.")
    $added += [int](Add-GigaEnvDefault -Path $envFile -Name "LOG_UPLOAD_URL" -Value "" -Comment "# Diagnostics: upload kiosk logs to photo_receiver. Empty URL reuses OUTPUT_UPLOAD_URL.")
    $added += [int](Add-GigaEnvDefault -Path $envFile -Name "LOG_UPLOAD_API_KEY" -Value "")
    $added += [int](Add-GigaEnvDefault -Path $envFile -Name "LOG_UPLOAD_AUTH" -Value "bearer")
    $added += [int](Add-GigaEnvDefault -Path $envFile -Name "LOG_UPLOAD_KIOSK_ID" -Value $env:COMPUTERNAME)
    $added += [int](Add-GigaEnvDefault -Path $envFile -Name "LOG_UPLOAD_INTERVAL_SEC" -Value "60")
    $added += [int](Add-GigaEnvDefault -Path $envFile -Name "LOG_UPLOAD_PATHS" -Value "data/srv_out.log;data/srv_err.log;server.log")
    $added += [int](Add-GigaEnvDefault -Path $envFile -Name "LOG_UPLOAD_MAX_BYTES" -Value "524288")
    $added += [int](Add-GigaEnvDefault -Path $envFile -Name "LOG_UPLOAD_INITIAL_TAIL_BYTES" -Value "262144")
    $added += [int](Add-GigaEnvDefault -Path $envFile -Name "OUTPUT_DISPATCH_FAIL_OPEN" -Value "true" -Comment "# Do not stop kiosk session if upload or print fails.")

    if ($added -gt 0) {
        Write-Host "[GIGAvibe] .env migration: added $added setting(s)." -ForegroundColor Green
    } else {
        Write-Host "[GIGAvibe] .env migration: no changes."
    }
}
