# optimize-gigavibe.ps1
# Configure GIGAvibe on the FARM machine (2x RTX 3090, Ryzen 5800X).
# - install CUDA build of torch (cu124)
# - re-pin numpy<2
# - write optimized .env
# - create GPU start script (pins inference to GPU0, adds torch/lib to PATH)
# - open firewall TCP 8765
# - verify CUDA providers

$ErrorActionPreference = "Continue"

$proj = "C:\Users\user\gigavibe"
$py = Join-Path $proj ".venv\Scripts\python.exe"
$pip = Join-Path $proj ".venv\Scripts\pip.exe"
$logDir = "$env:ProgramData\ssh-setup-logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$log = Join-Path $logDir ("gigavibe-optimize-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".log")

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts][$Level] $Message"
    Write-Host $line
    Add-Content -Path $log -Value $line -Encoding UTF8
}

function Set-EnvVar {
    param([string]$File, [string]$Key, [string]$Value)
    $line = "$Key=$Value"
    if (Test-Path $File) {
        $content = Get-Content $File
        if ($content -match "^\s*$([regex]::Escape($Key))\s*=") {
            $new = $content -replace "^\s*$([regex]::Escape($Key))\s*=.*$", $line
            Set-Content -Path $File -Value $new -Encoding UTF8
        } else {
            Add-Content -Path $File -Value $line -Encoding UTF8
        }
    } else {
        Set-Content -Path $File -Value $line -Encoding UTF8
    }
}

try {
    Write-Log "Start GIGAvibe optimization."

    # 1) CUDA build of torch matching onnxruntime-gpu 1.19.2 (CUDA 12.x, cuDNN 9)
    $torchCuda = (& $py -c "import torch;print(torch.version.cuda)" 2>$null)
    if ($torchCuda -and $torchCuda.Trim() -ne "" -and $torchCuda.Trim() -ne "None") {
        Write-Log "CUDA torch already installed (cuda $($torchCuda.Trim())), skip reinstall."
    } else {
        Write-Log "Installing CUDA torch (cu124)..."
        & $pip install --force-reinstall torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu124 2>&1 | Out-Null
        Write-Log "torch cu124 install finished (exit $LASTEXITCODE)."
    }

    # 2) onnxruntime-gpu needs numpy<2
    & $pip install "numpy>=1.24.4,<2" --force-reinstall 2>&1 | Out-Null
    Write-Log "numpy<2 re-pinned."

    # 3) torch lib path (cudnn DLLs live here)
    $torchLib = & $py -c "import torch,os;print(os.path.join(os.path.dirname(torch.__file__),'lib'))"
    $torchLib = $torchLib.Trim()
    Write-Log "torch lib: $torchLib"

    # 4) GPU start script: pin to GPU0 (headless), add torch/lib to PATH
    $startCmd = Join-Path $proj "start-gigavibe-gpu.cmd"
    $lines = @(
        "@echo off",
        "cd /d $proj",
        "set CUDA_VISIBLE_DEVICES=0",
        "set PATH=$torchLib;%PATH%",
        ".venv\Scripts\python.exe -m app.main"
    )
    Set-Content -Path $startCmd -Value $lines -Encoding ascii
    Write-Log "Start script written: $startCmd"

    # 5) Optimized .env for this machine (ASCII, no BOM; only valid Settings keys)
    $envFile = Join-Path $proj ".env"
    $envLines = @(
        "GENERATOR_MODE=ref_video",
        "HOST=0.0.0.0",
        "PORT=8765",
        "PUBLIC_BASE_URL=auto",
        "PRELOAD_MODEL_ON_STARTUP=true",
        "VIDEO_WIDTH=720",
        "VIDEO_HEIGHT=1280",
        "VIDEO_FPS=30",
        "VIDEO_DURATION_SEC=10",
        "VIDEO_ENCODE_CRF=16",
        "VIDEO_ENCODE_PRESET=slow",
        "REF_VIDEO_NO_UPSCALE=true",
        "REF_VIDEO_USE_SOURCE_FPS=true",
        "REF_VIDEO_FACE_RESTORE=true",
        "LIVEPORTRAIT_DEVICE_ID=0",
        "KIOSK_TEST_MODE=true",
        "USE_HTTPS=true",
        "SSL_CERTFILE=certs/cert.pem",
        "SSL_KEYFILE=certs/key.pem"
    )
    Set-Content -Path $envFile -Value $envLines -Encoding ascii
    Write-Log ".env optimized for FARM (GPU0, RTX 3090)."

    # 6) Firewall
    & netsh advfirewall firewall delete rule name=GIGAvibe-8765 2>&1 | Out-Null
    & netsh advfirewall firewall add rule name=GIGAvibe-8765 dir=in action=allow protocol=TCP localport=8765 2>&1 | Out-Null
    Write-Log "Firewall rule for 8765 ensured."

    # 7) Verify CUDA providers
    $env:CUDA_VISIBLE_DEVICES = "0"
    $env:PATH = "$torchLib;$env:PATH"
    Write-Log "Verifying CUDA..."
    $check = & $py (Join-Path $proj "remote\gpu_check.py") 2>&1
    foreach ($l in $check) { Write-Log "CHECK: $l" }

    Write-Log "Done. Start server with: $startCmd"
    Write-Log "Log file: $log"
    exit 0
}
catch {
    Write-Log "ERROR: $($_.Exception.Message)" "ERROR"
    Write-Log "Log file: $log" "ERROR"
    exit 1
}
