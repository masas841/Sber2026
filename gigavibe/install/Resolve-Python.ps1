function Get-GigaPython {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    $bundled = Join-Path $Root "runtime\python\python.exe"
    if (Test-Path $bundled) {
        return (Resolve-Path $bundled).Path
    }

    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    throw @"
Python was not found.
  Option 1: build the package with -IncludePython (bundles runtime\python)
  Option 2: install Python 3.10+ from python.org (Add to PATH)
"@
}

function Get-GigaVenvPython {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    $venvPy = Join-Path $Root ".venv\Scripts\python.exe"
    if (Test-Path $venvPy) {
        return (Resolve-Path $venvPy).Path
    }
    return Get-GigaPython -Root $Root
}
