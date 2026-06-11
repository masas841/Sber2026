# SB Sans woff2 для офлайн-киоска → web/fonts/
$ErrorActionPreference = "Stop"
$fontsDir = Join-Path $PSScriptRoot "..\web\fonts"
New-Item -ItemType Directory -Force -Path $fontsDir | Out-Null

$base = "https://cdn-app.sberdevices.ru/shared-static/0.0.0/fonts/SBSansText.0.2.0"
$fonts = @{
    "SBSansText-Semibold.woff2" = "$base/SBSansText-Semibold.woff2"
    "SBSansText-Medium.woff2"   = "$base/SBSansText-Medium.woff2"
}

foreach ($entry in $fonts.GetEnumerator()) {
    $out = Join-Path $fontsDir $entry.Key
    Write-Host "GET $($entry.Key)"
    Invoke-WebRequest -Uri $entry.Value -OutFile $out -UseBasicParsing
    Write-Host "  $((Get-Item $out).Length) bytes"
}

Write-Host "Done: $fontsDir"
