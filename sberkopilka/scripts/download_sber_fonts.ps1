# Скачивает SB Sans woff2 для офлайн-киоска → web/fonts/
$ErrorActionPreference = "Stop"
$fontsDir = Join-Path $PSScriptRoot "..\web\fonts"
New-Item -ItemType Directory -Force -Path $fontsDir | Out-Null

$fonts = @{
    "SBSansDisplay-Semibold.woff2" = "https://db.onlinewebfonts.com/t/2d130488c7306881cf236b40ea2a1020.woff2"
    "SBSansText-Medium.woff2"      = "https://db.onlinewebfonts.com/t/1207409a80c73135449c5e138309d114.woff2"
    "SBSansText-Semibold.woff2"    = "https://db.onlinewebfonts.com/t/cf8ad58acbe94cc96c1196fa2d336b14.woff2"
}

foreach ($entry in $fonts.GetEnumerator()) {
    $out = Join-Path $fontsDir $entry.Key
    Write-Host "GET $($entry.Key)"
    Invoke-WebRequest -Uri $entry.Value -OutFile $out -UseBasicParsing
    Write-Host "  $((Get-Item $out).Length) bytes"
}

Write-Host "Done: $fontsDir"
