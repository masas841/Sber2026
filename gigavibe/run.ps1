$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& .\.venv\Scripts\Activate.ps1
$env:PIP_DISABLE_PIP_VERSION_CHECK = "1"

function Invoke-Pip {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$PipArgs)
    $errPrev = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    & python -m pip @PipArgs 2>&1 | Out-Null
    $code = $LASTEXITCODE
    $ErrorActionPreference = $errPrev
    if ($code -ne 0) {
        throw "pip failed (exit $code): python -m pip $($PipArgs -join ' ')"
    }
}

function Test-PipPackage {
    param([string]$Package)
    $errPrev = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    & python -m pip show $Package *>$null
    $ok = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $errPrev
    return $ok
}

# Pin before anything else (onnxruntime-gpu 1.19 + ref_video need numpy<2)
Invoke-Pip install -c constraints.txt "numpy>=1.24.4,<2" "sympy==1.13.1" -q
Invoke-Pip install -c constraints.txt -r requirements.txt -q

# ref_video: only GPU build (never install package "onnxruntime" CPU)
if (Test-PipPackage "onnxruntime") {
    Invoke-Pip uninstall onnxruntime -y -q
}
Invoke-Pip install --no-deps "onnxruntime-gpu==1.19.2" -q
Invoke-Pip install coloredlogs flatbuffers packaging protobuf -q
Invoke-Pip install --no-deps "insightface>=0.7.3" -q
Invoke-Pip install onnx tqdm easydict prettytable scikit-image scikit-learn matplotlib -q
Invoke-Pip install -c constraints.txt "numpy>=1.24.4,<2" --force-reinstall -q

$torchLib = & python -c "import torch, os; print(os.path.join(os.path.dirname(torch.__file__), 'lib'))" 2>$null
if ($torchLib -and (Test-Path $torchLib)) {
    $env:PATH = "$torchLib;$env:PATH"
}

python -c "import onnxruntime as ort; assert hasattr(ort,'InferenceSession'); assert 'CUDAExecutionProvider' in ort.get_available_providers(); import insightface; print('[GIGAvibe] deps OK: onnxruntime-gpu', ort.__version__)"
if ($LASTEXITCODE -ne 0) {
    throw "onnxruntime-gpu / insightface not ready (see README ref_video)"
}

if (-not (Test-Path "models\gfpgan\GFPGANv1.4.pth")) {
    Write-Host "[GIGAvibe] GFPGAN model missing - run scripts\download_gfpgan.ps1 for face restore"
}

if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
    Write-Host "Created .env - set PUBLIC_BASE_URL to your LAN IP for QR codes"
}

Write-Host "Kiosk: http://127.0.0.1:8765  (health: /api/health)" -ForegroundColor Cyan
python -m app.main
