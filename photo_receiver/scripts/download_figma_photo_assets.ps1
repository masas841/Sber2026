# Figma Desktop MCP assets -> static/assets/figma/ (frame 138:194 «Гига5»)
$ErrorActionPreference = "Stop"
$out = Join-Path $PSScriptRoot "..\static\assets\figma" | Resolve-Path
New-Item -ItemType Directory -Force -Path $out | Out-Null

$base = "http://localhost:3845/assets"
$assets = @{
    "bg-generation.png"    = "9c03bdf0a15ed24d2b9590089c3aba95b33c04fb.png"
    "deco-3-3.png"         = "c7a4f71a7128ec5fd2ba7378b6db6378a5dce318.png"
    "sheet-leaf.png"       = "6acfd49bf21b76d402aa025507845b973f51eff4.png"
    "deco-2.png"           = "757708fa0b9ab7470e1502b4db90b267c9616919.png"
    "flower.png"           = "12e43c742fcd3f9652f442f2d9d21465edb23ecd.png"
    "deco-4.png"           = "207c75fcd13674e07e6be35020f2608d881f6dab.png"
    "ellipse-blob-a.svg"   = "eb5ad096fa59d1fccd5796c7c469693afecb7169.svg"
    "ellipse-blob-b.svg"   = "de26049cd0420f1d1114fb474fd1728b9f3195bb.svg"
    "ellipse-glow-1.svg"   = "4df9d9a42f11c6c505e32b4bfaa38f2e8446238e.svg"
    "ellipse-glow-2.svg"   = "215e4dcc3d22faa91cd90e7946a7e0037a0f9dbd.svg"
    "ellipse-glow-3.svg"   = "85a1b931040075ff86bd2bf86e3c6e589b6911ca.svg"
    "giga-full.svg"        = "e8d5b6ac5cb6249aa57e0e97fbff75aeeb3be447.svg"
}

foreach ($entry in $assets.GetEnumerator()) {
    $dest = Join-Path $out $entry.Key
    Write-Host "GET $($entry.Key)"
    Invoke-WebRequest -Uri "$base/$($entry.Value)" -OutFile $dest -UseBasicParsing
    Write-Host "  $((Get-Item $dest).Length) bytes"
}

Write-Host "Done: $out"

$py = Join-Path (Split-Path $PSScriptRoot -Parent) ".venv\Scripts\python.exe"
$gigaPy = Join-Path (Split-Path $PSScriptRoot -Parent) "..\gigavibe\.venv\Scripts\python.exe"
$compress = Join-Path $PSScriptRoot "compress_photo_assets.py"
if (Test-Path $gigaPy) { & $gigaPy $compress }
elseif (Test-Path $py) { & $py $compress }
else { Write-Host "WARN: run compress_photo_assets.py manually (needs Pillow)" }
