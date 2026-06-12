function Ensure-GigaVcRedist {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root,
        [switch]$Offline
    )

    $redistDir = Join-Path $Root "install\redist"
    $redistExe = Join-Path $redistDir "vc_redist.x64.exe"
    $redistUrl = "https://aka.ms/vs/17/release/vc_redist.x64.exe"

    if (-not (Test-Path $redistExe)) {
        if ($Offline) {
            throw "Offline mode: install\redist\vc_redist.x64.exe is missing."
        }
        New-Item -ItemType Directory -Force -Path $redistDir | Out-Null
        Write-Host "Downloading Microsoft Visual C++ Redistributable x64 ..."
        Invoke-WebRequest -Uri $redistUrl -OutFile $redistExe -UseBasicParsing
    }

    Write-Host "Installing Microsoft Visual C++ Redistributable x64 ..."
    $proc = Start-Process -FilePath $redistExe -ArgumentList "/install", "/quiet", "/norestart" -Wait -PassThru
    if ($proc.ExitCode -ne 0 -and $proc.ExitCode -ne 3010) {
        throw "vc_redist.x64.exe failed with exit code $($proc.ExitCode)"
    }
    if ($proc.ExitCode -eq 3010) {
        Write-Host "WARN: Visual C++ Redistributable requests reboot. Continue, but reboot if CUDA DLL loading still fails." -ForegroundColor Yellow
    }
}
