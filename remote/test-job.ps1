# Тестовый job: отправляет test_face.jpg, опрашивает статус, печатает тайминги.
$ErrorActionPreference = "Stop"
Set-Location C:\Users\user\gigavibe
[System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }

$photo = "data\test_face.jpg"
if (-not (Test-Path $photo)) { throw "no $photo" }

$base = "https://127.0.0.1:8765"

# multipart через curl.exe (надёжно для файлов)
$created = & curl.exe -sk -F "photo=@$photo" "$base/api/jobs"
Write-Output ("create: " + $created)
$jobId = ($created | ConvertFrom-Json).job_id
if (-not $jobId) { throw "no job_id" }

for ($i = 0; $i -lt 180; $i++) {
    Start-Sleep -Seconds 2
    $raw = & curl.exe -sk "$base/api/jobs/$jobId"
    $data = $raw | ConvertFrom-Json
    if ($data.status -eq "done") {
        Write-Output "=== DONE ==="
        Write-Output $raw
        break
    }
    if ($data.status -eq "error") {
        Write-Output "=== ERROR ==="
        Write-Output $raw
        break
    }
    if ($i % 5 -eq 0) { Write-Output ("... " + $data.status + " : " + $data.message) }
}
