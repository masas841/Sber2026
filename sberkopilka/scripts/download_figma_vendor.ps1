# Локальные зависимости для figma-screens (офлайн-киоск)
$ErrorActionPreference = "Stop"
$vendor = Join-Path $PSScriptRoot "..\web\vendor"
New-Item -ItemType Directory -Force -Path $vendor | Out-Null

$files = @{
    "react.production.min.js"     = "https://unpkg.com/react@18.3.1/umd/react.production.min.js"
    "react-dom.production.min.js" = "https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js"
    "babel.min.js"                = "https://unpkg.com/@babel/standalone@7.26.9/babel.min.js"
    "tailwindcdn.min.js"          = "https://cdn.tailwindcss.com"
}

foreach ($name in $files.Keys) {
    $dest = Join-Path $vendor $name
    Write-Host "Downloading $name ..."
    Invoke-WebRequest -Uri $files[$name] -OutFile $dest -UseBasicParsing
    $size = (Get-Item $dest).Length
    Write-Host "  OK ($size bytes)"
}

Write-Host "Done. Vendor files in $vendor"
