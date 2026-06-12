# InstantID pipeline without git clone - raw files from GitHub.
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$dest = Join-Path $root "vendor\instantid"
$ipdir = Join-Path $dest "ip_adapter"
New-Item -ItemType Directory -Path $dest -Force | Out-Null
New-Item -ItemType Directory -Path $ipdir -Force | Out-Null

$base = "https://raw.githubusercontent.com/instantX-research/InstantID/main"
$files = @{
    (Join-Path $dest "pipeline_stable_diffusion_xl_instantid.py") = "$base/pipeline_stable_diffusion_xl_instantid.py"
    (Join-Path $ipdir "resampler.py")                              = "$base/ip_adapter/resampler.py"
    (Join-Path $ipdir "utils.py")                                  = "$base/ip_adapter/utils.py"
    (Join-Path $ipdir "attention_processor.py")                    = "$base/ip_adapter/attention_processor.py"
}

foreach ($kv in $files.GetEnumerator()) {
    curl.exe -sL -o $kv.Key $kv.Value
    if (-not (Test-Path $kv.Key)) { throw "Failed: $($kv.Value)" }
    Write-Host ("OK {0}" -f (Split-Path $kv.Key -Leaf))
}

Set-Content -Path (Join-Path $ipdir "__init__.py") -Value "" -Encoding ascii

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "No venv: run run.ps1 first" }
$hasEinops = & $py -c "import importlib.util; print('1' if importlib.util.find_spec('einops') else '0')"
if ($hasEinops -ne "1") {
    & (Join-Path $root ".venv\Scripts\pip.exe") install einops -q
}
Write-Host "vendor/instantid ready: $dest"
