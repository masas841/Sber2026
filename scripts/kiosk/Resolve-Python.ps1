function Get-KioskPython {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    function Resolve-KioskPythonCandidate {
        param([string]$Candidate)

        if (-not $Candidate) {
            return $null
        }

        $source = $Candidate
        if ($source -like "*\WindowsApps\python*.exe") {
            return $null
        }

        $oldErrorActionPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $resolved = & $source -c "import sys; print(sys.executable)" 2>$null
            $code = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $oldErrorActionPreference
        }

        if ($code -eq 0 -and $resolved) {
            return ([string]$resolved).Trim()
        }
        return $null
    }

    $bundled = Join-Path $Root "runtime\python\python.exe"
    if (Test-Path $bundled) {
        return (Resolve-Path $bundled).Path
    }

    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) {
        $python = Resolve-KioskPythonCandidate -Candidate $cmd.Source
        if ($python) {
            return $python
        }
    }

    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        $oldErrorActionPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $python = & $py.Source -3 -c "import sys; print(sys.executable)" 2>$null
            $code = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $oldErrorActionPreference
        }

        if ($code -eq 0 -and $python) {
            return ([string]$python).Trim()
        }
    }

    throw @"
Python was not found.
  Option 1: build the package with -IncludePython (bundles runtime\python)
  Option 2: install Python 3.10+ from python.org (Add to PATH)
  Note: Microsoft Store "python.exe" app execution alias is ignored because it is not a real Python runtime.
"@
}

function Get-KioskVenvPython {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    $venvPy = Join-Path $Root ".venv\Scripts\python.exe"
    if (Test-Path $venvPy) {
        return (Resolve-Path $venvPy).Path
    }
    return Get-KioskPython -Root $Root
}

function New-KioskVenv {
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
