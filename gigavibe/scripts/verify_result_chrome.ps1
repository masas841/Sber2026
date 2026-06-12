# Capture result screen screenshot with headless Chrome and self-signed HTTPS.
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$Out = Join-Path $PSScriptRoot "_verify_result.png"
$Port = if ($env:PORT) { $env:PORT } else { "8765" }
$Scheme = if ($env:USE_HTTPS -eq "false") { "http" } else { "https" }
$ChromeFlags = @("--headless=new", "--disable-gpu", "--window-size=1008,672", "--hide-scrollbars")
if ($Scheme -eq "https") {
    $ChromeFlags += "--ignore-certificate-errors"
}
$Url = "${Scheme}://127.0.0.1:${Port}/?preview=result"

$chrome = Join-Path ${env:ProgramFiles} "Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $chrome)) {
    $chrome = Join-Path ${env:ProgramFiles(x86)} "Google\Chrome\Application\chrome.exe"
}
if (-not (Test-Path $chrome)) {
    Write-Error "Google Chrome was not found"
}

if (Test-Path $Out) { Remove-Item $Out -Force }

& $chrome @ChromeFlags --screenshot=$Out $Url

if (-not (Test-Path $Out)) {
    Write-Error "Screenshot was not created. Is the server running at $Url?"
}

$bytes = (Get-Item $Out).Length
Write-Host "OK: $Out ($bytes bytes)"
Write-Host "URL: $Url"
