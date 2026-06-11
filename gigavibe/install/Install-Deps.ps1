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

    function Invoke-Pip {
        param([Parameter(ValueFromRemainingArguments = $true)][string[]]$PipArgs)
        & python -m pip @PipArgs
        if ($LASTEXITCODE -ne 0) {
            throw "pip failed: python -m pip $($PipArgs -join ' ')"
        }
    }

    Invoke-Pip install @findLinks -c constraints.txt "numpy>=1.24.4,<2" "sympy==1.13.1" -q
    Invoke-Pip install @findLinks -c constraints.txt -r requirements-kiosk.txt -q

    if (-not $offline) {
        Invoke-Pip uninstall onnxruntime -y -q 2>$null
    }
    Invoke-Pip install @findLinks --no-deps "onnxruntime-gpu==1.19.2" -q
    Invoke-Pip install @findLinks coloredlogs flatbuffers packaging protobuf -q
    Invoke-Pip install @findLinks --no-deps "insightface>=0.7.3" -q
    Invoke-Pip install @findLinks onnx tqdm easydict prettytable scikit-image scikit-learn matplotlib -q
    Invoke-Pip install @findLinks -c constraints.txt "numpy>=1.24.4,<2" --force-reinstall -q

    & python -c "import onnxruntime as ort; import insightface; print('deps OK:', ort.__version__)"
    if ($LASTEXITCODE -ne 0) {
        throw "onnxruntime-gpu / insightface не установились"
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
    if (Test-Path $venvDir) {
        Remove-Item $venvDir -Recurse -Force
    }

    & $BasePython -m venv $venvDir 2>$null
    if ($LASTEXITCODE -ne 0) {
        & $BasePython -m virtualenv $venvDir
        if ($LASTEXITCODE -ne 0) {
            throw "venv/virtualenv failed for $BasePython"
        }
    }
}
