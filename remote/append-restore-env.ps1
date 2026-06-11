# Добавляет настройки ускорения GFPGAN в .env (ASCII без BOM, идемпотентно).
$ErrorActionPreference = "Stop"
Set-Location C:\Users\user\gigavibe

$pairs = @{
    "REF_VIDEO_RESTORE_EVERY_N"          = "1"
    "REF_VIDEO_RESTORE_INTERPOLATE"      = "true"
    "REF_VIDEO_INLINE_RESTORE"           = "true"
    "REF_VIDEO_INLINE_RESTORE_WEIGHT"    = "0.5"
    "REF_VIDEO_RESTORE_WORKERS"          = "2"
    "REF_VIDEO_SWAP_ENGINE"              = "inswapper_fast"
    "INSWAPPER_FAST_MODEL_PATH"          = "C:\Users\user\gigavibe\models\inswapper_128.onnx"
    "REF_VIDEO_LEAN_DETECT"              = "true"
    "REF_VIDEO_THREADED_READ"            = "true"
    "REF_VIDEO_READ_QUEUE"               = "8"
    "REF_VIDEO_SERIALIZE_JOBS"           = "true"
    "REF_VIDEO_SWAP_WORKERS"             = "1"
}

$lines = if (Test-Path .env) { Get-Content .env } else { @() }

foreach ($key in $pairs.Keys) {
    $val = $pairs[$key]
    $pattern = "^\s*$key\s*="
    $idx = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match $pattern) { $idx = $i; break }
    }
    if ($idx -ge 0) {
        $lines[$idx] = "$key=$val"
    } else {
        $lines += "$key=$val"
    }
}

# ASCII без BOM
[System.IO.File]::WriteAllLines("C:\Users\user\gigavibe\.env", $lines, (New-Object System.Text.ASCIIEncoding))

Write-Output "--- .env REF_VIDEO optimization flags ---"
Get-Content .env | Where-Object { $_ -match "REF_VIDEO_(RESTORE|INLINE|SWAP|LEAN|THREADED|READ_QUEUE|SERIALIZE_JOBS|SWAP_WORKERS)|INSWAPPER_FAST" }
