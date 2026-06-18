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

function Ensure-SmilePayMediaPipeVendor {
    param([string]$Root)

    $bundle = Join-Path $Root "web\vendor\mediapipe\tasks-vision\vision_bundle.mjs"
    if (Test-Path $bundle) { return }
    $script = Join-Path $Root "scripts\download_mediapipe_tasks_vision.ps1"
    if (-not (Test-Path $script)) {
        Write-Host "[SmilePay] WARN: MediaPipe vendor missing and download script not found" -ForegroundColor Yellow
        return
    }
    Write-Host "[SmilePay] Downloading local MediaPipe tasks-vision (offline WASM)..." -ForegroundColor Yellow
    & $script
}

function Ensure-SmilePayFaceModel {
    param([string]$Root)

    $model = Join-Path $Root "web\models\face_landmarker.task"
    if (Test-Path $model) { return }
    $script = Join-Path $Root "scripts\download_smile_model.ps1"
    if (-not (Test-Path $script)) {
        Write-Host "[SmilePay] WARN: face_landmarker.task missing and download script not found" -ForegroundColor Yellow
        return
    }
    Write-Host "[SmilePay] Downloading face_landmarker.task ..." -ForegroundColor Yellow
    & $script
}

function Update-SmilePayEnvDefaults {
    param([string]$Root)

    $envFile = Join-Path $Root ".env"
    $example = Join-Path $Root "install\.env.kiosk.example"
    if (-not (Test-Path $envFile)) {
        if (Test-Path $example) {
            Copy-Item $example $envFile
            Write-Host "[SmilePay] Created .env from install\.env.kiosk.example" -ForegroundColor Yellow
        } else {
            New-Item -ItemType File -Path $envFile -Force | Out-Null
        }
    }

    $added = 0
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "PLAY_LOG_FILE" -Value "data/plays.jsonl" -Comment "# Persistent play log for daily stats.")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "PLAY_LOG_TZ" -Value "Europe/Moscow")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "AUTO_UPDATE_FROM_GITHUB" -Value "false" -Comment "# Updater: pull latest app files from GitHub before launch.")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "UPDATE_REPO_REF" -Value "main")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "UPDATE_MANIFEST_URL" -Value "https://raw.githubusercontent.com/masas841/Sber2026/main/smile-pay/install/update-manifest.json")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "UPDATE_RAW_BASE_URL" -Value "https://raw.githubusercontent.com/masas841/Sber2026/main/smile-pay")
    $added += [int](Add-KioskEnvDefault -Path $envFile -Name "UPDATE_REPO_ARCHIVE_URL" -Value "https://github.com/masas841/Sber2026/archive/refs/heads/main.zip")

    if ($added -gt 0) {
        Write-Host "[SmilePay] .env migration: added $added setting(s)." -ForegroundColor Green
    }
}

function Invoke-SmilePayPostUpdateHooks {
    param([string]$Root)

    Update-SmilePayEnvDefaults -Root $Root
    Ensure-SmilePayMediaPipeVendor -Root $Root
    Ensure-SmilePayFaceModel -Root $Root
}
