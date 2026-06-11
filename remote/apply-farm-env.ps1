# Merge remote/farm-*.env -> .env, сохраняя секреты из текущего .env
param(
    [string]$EnvTemplate = "farm-nanobanana.env"
)
$ErrorActionPreference = "Stop"
$proj = "C:\Users\user\gigavibe"
$farm = Join-Path $proj "remote\$EnvTemplate"
$envPath = Join-Path $proj ".env"
if (-not (Test-Path $farm)) {
    throw "Не найден $farm"
}

$preserveKeys = @("HF_TOKEN", "AITUNNEL_API_KEY", "NANOBANANA_API_KEY", "QUATARLY_API_KEY", "GEMINI_API_KEY")
$preserved = @{}
if (Test-Path $envPath) {
    foreach ($line in Get-Content $envPath -Encoding UTF8) {
        foreach ($key in $preserveKeys) {
            if ($line -match "^\s*$key\s*=") {
                $preserved[$key] = $line.Trim()
            }
        }
    }
}

Copy-Item $farm $envPath -Force
$lines = Get-Content $envPath -Encoding UTF8
$out = New-Object System.Collections.Generic.List[string]
foreach ($line in $lines) {
    $skip = $false
    foreach ($key in $preserveKeys) {
        if ($line -match "^\s*$key\s*=") {
            if ($preserved.ContainsKey($key)) {
                $out.Add($preserved[$key])
            } else {
                $out.Add($line)
            }
            $skip = $true
            break
        }
    }
    if (-not $skip) { $out.Add($line) }
}
foreach ($key in $preserveKeys) {
    if ($preserved.ContainsKey($key) -and -not ($out | Where-Object { $_ -match "^\s*$key\s*=" })) {
        $out.Add($preserved[$key])
    }
}
$out | Set-Content $envPath -Encoding ascii
Write-Host "[deploy] .env обновлён из $EnvTemplate"
