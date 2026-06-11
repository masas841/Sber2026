# Запуск GIGAvibe-сервиса как фонового процесса (для удалённого старта по SSH).
# Грузит модели резидентно (warmup при старте), пишет логи в data\.
$ErrorActionPreference = "Stop"
$root = "C:\Users\user\gigavibe"
Set-Location $root

# torch\lib в PATH — нужно для onnxruntime-gpu / CUDA DLL
$torchLib = Join-Path $root ".venv\Lib\site-packages\torch\lib"
if (Test-Path $torchLib) { $env:PATH = "$torchLib;$env:PATH" }

$py = Join-Path $root ".venv\Scripts\python.exe"
$proc = Start-Process -FilePath $py -ArgumentList "-m", "app.main" `
    -WorkingDirectory $root `
    -RedirectStandardOutput (Join-Path $root "data\srv_out.log") `
    -RedirectStandardError  (Join-Path $root "data\srv_err.log") `
    -WindowStyle Hidden -PassThru
Write-Host ("PID=" + $proc.Id)
