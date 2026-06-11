# Вендоринг InstantID без git: качаем нужные .py напрямую с GitHub raw.
$ErrorActionPreference = "Continue"
$dest = "C:\Users\user\gigavibe\vendor\instantid"
$ipdir = Join-Path $dest "ip_adapter"
New-Item -ItemType Directory -Path $dest -Force | Out-Null
New-Item -ItemType Directory -Path $ipdir -Force | Out-Null

$base = "https://raw.githubusercontent.com/instantX-research/InstantID/main"
$files = @{
    "$dest\pipeline_stable_diffusion_xl_instantid.py" = "$base/pipeline_stable_diffusion_xl_instantid.py"
    "$ipdir\resampler.py"                              = "$base/ip_adapter/resampler.py"
    "$ipdir\utils.py"                                  = "$base/ip_adapter/utils.py"
    "$ipdir\attention_processor.py"                    = "$base/ip_adapter/attention_processor.py"
}

foreach ($kv in $files.GetEnumerator()) {
    $out = $kv.Key
    $url = $kv.Value
    & curl.exe -sL -o $out $url
    if (Test-Path $out) {
        $sz = (Get-Item $out).Length
        Write-Host ("OK {0} ({1} bytes)" -f (Split-Path $out -Leaf), $sz)
    } else {
        Write-Host ("FAIL {0}" -f $url)
    }
}

# __init__.py для пакета ip_adapter
Set-Content -Path (Join-Path $ipdir "__init__.py") -Value "" -Encoding ascii

# Проверка einops (нужен resampler.py)
$py = "C:\Users\user\gigavibe\.venv\Scripts\python.exe"
$hasEinops = & $py -c "import importlib.util,sys; sys.stdout.write('1' if importlib.util.find_spec('einops') else '0')"
if ($hasEinops -ne "1") {
    Write-Host "Installing einops..."
    & "C:\Users\user\gigavibe\.venv\Scripts\pip.exe" install einops 2>&1 | Out-Null
}
Write-Host "einops present: $hasEinops"
Write-Host "Vendored to $dest"
