@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  GIGAvibe - LTX-Video download
echo  ~15-25 GB -^> models\LTX-Video
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 goto :error
    call .venv\Scripts\activate.bat
    echo [2/3] Installing dependencies...
    pip install -r requirements.txt
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
) else (
    call .venv\Scripts\activate.bat
)

set HF_HUB_DISABLE_SYMLINKS_WARNING=1

REM HF_TOKEN is read from .env inside the Python script.

echo [3/3] Downloading model...
echo.
echo  This window will show:
echo    - downloaded GB
echo    - speed MB/s
echo    - file count
echo.
echo  Full log: data\ltx_download_log.txt
echo.

set PYTHONUNBUFFERED=1
.venv\Scripts\python.exe -u scripts\download_ltx.py
set EXITCODE=%ERRORLEVEL%

echo.
if %EXITCODE% EQU 0 (
    echo ========================================
    echo  Done! models\LTX-Video
    echo  In .env: GENERATOR_MODE=ltx
    echo  Run: run.ps1
    echo ========================================
) else (
    echo ========================================
    echo  Error. Code: %EXITCODE%
    echo  See data\ltx_download_log.txt
    echo ========================================
    goto :error
)

pause
exit /b 0

:error
pause
exit /b 1
