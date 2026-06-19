function Install-KioskPipDeps {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root,
        [string]$WheelsDir = "",
        [string]$RequirementsFile = "requirements.txt"
    )

    Set-Location $Root
    $env:PIP_DISABLE_PIP_VERSION_CHECK = "1"

    $reqPath = Join-Path $Root $RequirementsFile
    if (-not (Test-Path $reqPath)) {
        throw "Requirements file not found: $reqPath"
    }

    $offline = $WheelsDir -and (Test-Path $WheelsDir)
    $findLinks = @()
    if ($offline) {
        $findLinks += "--no-index", "--find-links", $WheelsDir
    }

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

    Invoke-Pip install @findLinks --upgrade pip -q
    Invoke-Pip install @findLinks -r $RequirementsFile -q
    & python -c "import fastapi, uvicorn; print('deps OK:', fastapi.__version__)"
    if ($LASTEXITCODE -ne 0) {
        throw "fastapi / uvicorn installation failed"
    }
}
