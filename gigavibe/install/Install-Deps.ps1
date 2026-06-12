function Install-GigaKioskDeps {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root,
        [string]$WheelsDir = ""
    )

    Set-Location $Root
    $env:PIP_DISABLE_PIP_VERSION_CHECK = "1"

    $offline = $WheelsDir -and (Test-Path $WheelsDir)
    $findLinks = @()
    if ($offline) {
        $findLinks += "--no-index", "--find-links", $WheelsDir
    }
    $torchSpec = "torch==2.4.1+cu121"
    $torchIndexUrl = "https://download.pytorch.org/whl/cu121"
    $onnxRuntimeGpuSpec = "onnxruntime-gpu==1.19.2"

    function Invoke-Pip {
        param([Parameter(ValueFromRemainingArguments = $true)][string[]]$PipArgs)
        $oldErrorActionPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $output = & python -m pip @PipArgs 2>&1
            $code = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $oldErrorActionPreference
        }
        foreach ($line in $output) {
            Write-Host $line
        }
        if ($code -ne 0) {
            throw "pip failed: python -m pip $($PipArgs -join ' ')"
        }
    }

    function Add-GigaTorchLibPath {
        $torchLib = & python -c "import os, torch; print(os.path.join(os.path.dirname(torch.__file__), 'lib'))" 2>$null
        if ($LASTEXITCODE -eq 0 -and $torchLib -and (Test-Path $torchLib)) {
            $env:PATH = "$torchLib;$env:PATH"
            Write-Host "CUDA DLL path: $torchLib"
            return $true
        }
        return $false
    }

    Invoke-Pip install @findLinks -c constraints.txt "numpy>=1.24.4,<2" "sympy==1.13.1" -q
    Invoke-Pip install @findLinks -c constraints.txt -r requirements-kiosk.txt -q

    if (-not $offline) {
        Invoke-Pip uninstall onnxruntime -y -q 2>$null
    }
    if ($offline) {
        Invoke-Pip install @findLinks $torchSpec -q
    } else {
        Invoke-Pip install $torchSpec --index-url $torchIndexUrl -q
    }
    if (-not (Add-GigaTorchLibPath)) {
        throw "torch CUDA DLL path was not found"
    }
    Invoke-Pip install @findLinks --no-deps $onnxRuntimeGpuSpec -q
    Invoke-Pip install @findLinks coloredlogs flatbuffers packaging protobuf -q
    Invoke-Pip install @findLinks --no-deps "insightface>=0.7.3" -q
    Invoke-Pip install @findLinks opencv-python onnx tqdm easydict prettytable scikit-image scikit-learn matplotlib -q
    Invoke-Pip install @findLinks -c constraints.txt "numpy>=1.24.4,<2" --force-reinstall -q

    Add-GigaTorchLibPath | Out-Null
    & python -c "import onnxruntime as ort; import insightface; print('deps OK:', ort.__version__, ort.get_available_providers())"
    if ($LASTEXITCODE -ne 0) {
        throw "onnxruntime-gpu / insightface installation failed"
    }
}

function New-GigaVenv {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root,
        [Parameter(Mandatory = $true)]
        [string]$BasePython
    )

    $venvDir = Join-Path $Root ".venv"
    $venvPy = Join-Path $venvDir "Scripts\python.exe"
    if (Test-Path $venvDir) {
        Remove-Item $venvDir -Recurse -Force
    }

    $oldErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $BasePython -c "import venv" *> $null
        $hasVenv = $LASTEXITCODE -eq 0

        $venvFailed = $true
        if ($hasVenv) {
            Write-Host "Creating .venv with venv ..."
            & $BasePython -m venv $venvDir
            $venvFailed = $LASTEXITCODE -ne 0
        }

        if ($venvFailed -or -not (Test-Path $venvPy)) {
            if (Test-Path $venvDir) {
                Remove-Item $venvDir -Recurse -Force
            }
            Write-Host "Creating .venv with virtualenv ..."
            & $BasePython -m virtualenv $venvDir
            if (-not (Test-Path $venvPy)) {
                throw "venv/virtualenv failed for $BasePython"
            }
        }
    } finally {
        $ErrorActionPreference = $oldErrorActionPreference
    }
}
