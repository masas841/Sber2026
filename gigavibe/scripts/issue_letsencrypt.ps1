# Выпуск Let's Encrypt для GIGAvibe (DNS-01 через Beget).
# Домен должен указывать на ваш публичный IP (A-запись).
#
# Подготовка:
#   1. В панели Beget → «API» → включить API, задать пароль API.
#   2. Создать файл .env.ssl рядом с .env (см. .env.ssl.example).
#   3. Запуск от обычного пользователя (порт 80 не нужен).
#
# Использование:
#   .\scripts\issue_letsencrypt.ps1
#   .\scripts\issue_letsencrypt.ps1 -Domain slash.omelchak.com -Email admin@omelchak.com

[CmdletBinding()]
param(
    [string]$Domain = "slash.omelchak.com",
    [string]$Email = "admin@omelchak.com",
    [string]$ProjectRoot = (Split-Path $PSScriptRoot -Parent)
)

$ErrorActionPreference = "Stop"

function Read-DotEnvFile {
    param([string]$Path)
    $vars = @{}
    if (-not (Test-Path $Path)) { return $vars }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $idx = $line.IndexOf("=")
        if ($idx -lt 1) { return }
        $key = $line.Substring(0, $idx).Trim()
        $val = $line.Substring($idx + 1).Trim()
        if ($val.StartsWith('"') -and $val.EndsWith('"')) { $val = $val.Substring(1, $val.Length - 2) }
        $vars[$key] = $val
    }
    return $vars
}

function Ensure-Lego {
    param([string]$ToolsDir)
    $legoExe = Join-Path $ToolsDir "lego\lego.exe"
    if (Test-Path $legoExe) { return $legoExe }

    New-Item -ItemType Directory -Force -Path (Join-Path $ToolsDir "lego") | Out-Null
    $zip = Join-Path $env:TEMP "lego_windows_amd64.zip"
    $url = "https://github.com/go-acme/lego/releases/download/v4.23.1/lego_v4.23.1_windows_amd64.zip"
    Write-Host "[ssl] Скачиваю lego..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $url -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath (Join-Path $ToolsDir "lego") -Force
    if (-not (Test-Path $legoExe)) { throw "lego.exe не найден после распаковки" }
    return $legoExe
}

$envFile = Join-Path $ProjectRoot ".env.ssl"
$dotenv = Read-DotEnvFile $envFile
$begetUser = $env:BEGET_USERNAME
if (-not $begetUser) { $begetUser = $dotenv["BEGET_USERNAME"] }
$begetPass = $env:BEGET_PASSWORD
if (-not $begetPass) { $begetPass = $dotenv["BEGET_PASSWORD"] }
if ($dotenv["SSL_EMAIL"]) { $Email = $dotenv["SSL_EMAIL"] }
if ($dotenv["SSL_DOMAIN"]) { $Domain = $dotenv["SSL_DOMAIN"] }

if (-not $begetUser -or -not $begetPass) {
    throw @"
Не заданы BEGET_USERNAME / BEGET_PASSWORD.
Создайте файл $envFile по образцу .env.ssl.example
(пароль API — в панели Beget → Настройки → Доступ по API).
"@
}

$toolsDir = Join-Path $ProjectRoot "tools"
$legoExe = Ensure-Lego -ToolsDir $toolsDir
$acmeDir = Join-Path $ProjectRoot "certs\acme"
$certsDir = Join-Path $ProjectRoot "certs"
New-Item -ItemType Directory -Force -Path $acmeDir | Out-Null

$env:BEGET_USERNAME = $begetUser
$env:BEGET_PASSWORD = $begetPass

Write-Host "[ssl] Домен: $Domain" -ForegroundColor Cyan
Write-Host "[ssl] Email: $Email" -ForegroundColor Cyan
Write-Host "[ssl] DNS-провайдер: Beget (DNS-01)..." -ForegroundColor Cyan

& $legoExe --email $Email --dns beget -d $Domain --path $acmeDir --accept-tos run
if ($LASTEXITCODE -ne 0) { throw "lego завершился с кодом $LASTEXITCODE" }

$certSrc = Join-Path $acmeDir "certificates\$Domain.crt"
$keySrc = Join-Path $acmeDir "certificates\$Domain.key"
$issuerSrc = Join-Path $acmeDir "certificates\$Domain.issuer.crt"
if (-not (Test-Path $certSrc) -or -not (Test-Path $keySrc)) {
    throw "Сертификаты не найдены в $acmeDir\certificates"
}

$certDst = Join-Path $certsDir "cert.pem"
$keyDst = Join-Path $certsDir "key.pem"
$backupStamp = Get-Date -Format "yyyyMMdd-HHmmss"
foreach ($pair in @(
    @{ Src = $certDst; Name = "cert.pem" },
    @{ Src = $keyDst; Name = "key.pem" }
)) {
    if (Test-Path $pair.Src) {
        Copy-Item $pair.Src (Join-Path $certsDir "$($pair.Name).bak-$backupStamp") -Force
    }
}

if (Test-Path $issuerSrc) {
    Get-Content $certSrc, $issuerSrc | Set-Content -Path $certDst -Encoding ascii
} else {
    Copy-Item $certSrc $certDst -Force
}
Copy-Item $keySrc $keyDst -Force

Write-Host "[ssl] Готово:" -ForegroundColor Green
Write-Host "  $certDst"
Write-Host "  $keyDst"

# Обновить .env: PUBLIC_BASE_URL и пути к сертификатам
$mainEnv = Join-Path $ProjectRoot ".env"
if (Test-Path $mainEnv) {
    $lines = Get-Content $mainEnv
    $publicUrl = "https://${Domain}:8765"
    $updated = $false
    $newLines = foreach ($line in $lines) {
        if ($line -match '^\s*PUBLIC_BASE_URL=') { $updated = $true; "PUBLIC_BASE_URL=$publicUrl" }
        elseif ($line -match '^\s*USE_HTTPS=') { "USE_HTTPS=true" }
        elseif ($line -match '^\s*SSL_CERTFILE=') { "SSL_CERTFILE=certs/cert.pem" }
        elseif ($line -match '^\s*SSL_KEYFILE=') { "SSL_KEYFILE=certs/key.pem" }
        else { $line }
    }
    if (-not $updated) { $newLines += "PUBLIC_BASE_URL=$publicUrl" }
    Set-Content -Path $mainEnv -Value $newLines -Encoding UTF8
    Write-Host "[ssl] .env обновлён: PUBLIC_BASE_URL=$publicUrl" -ForegroundColor Green
}

Write-Host "[ssl] Перезапустите сервер: python -m app.main" -ForegroundColor Yellow
Write-Host "[ssl] Проброс на роутере: TCP 8765 -> этот ПК (для доступа с телефона по домену)." -ForegroundColor Yellow
