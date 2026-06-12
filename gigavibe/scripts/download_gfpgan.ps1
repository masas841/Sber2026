# Download GFPGANv1.4.pth for REF_VIDEO_FACE_RESTORE.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

$dest = "models\gfpgan\GFPGANv1.4.pth"
New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null

if ((Test-Path $dest) -and ((Get-Item $dest).Length -gt 1MB)) {
    Write-Host "Already exists: $dest"
    exit 0
}

$urls = @(
    "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.4/GFPGANv1.4.pth",
    "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth",
    "https://huggingface.co/grokcv/GFPGAN/resolve/main/GFPGANv1.4.pth"
)

foreach ($url in $urls) {
    Write-Host "Trying $url"
    try {
        Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
        if ((Get-Item $dest).Length -gt 1MB) {
            Write-Host "OK: $dest"
            exit 0
        }
    } catch {
        Write-Warning $_
        Remove-Item $dest -ErrorAction SilentlyContinue
    }
}

throw "Download failed. Copy GFPGANv1.4.pth manually to $dest"
