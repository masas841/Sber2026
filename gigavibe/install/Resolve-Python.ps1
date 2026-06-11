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
Python не найден.
  Вариант 1: соберите пакет с -IncludePython (внутри будет runtime\python)
  Вариант 2: установите Python 3.10+ с python.org (Add to PATH)
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
