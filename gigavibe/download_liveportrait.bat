@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  GIGAvibe - LivePortrait
echo  vendor\LivePortrait + .venv-liveportrait
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [0] Creating kiosk .venv...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

set HF_HUB_DISABLE_SYMLINKS_WARNING=1
set PYTHONUNBUFFERED=1

echo Installing LivePortrait (git + venv + weights)...
echo Log: data\liveportrait_download_log.txt
echo.

.venv\Scripts\python.exe -u scripts\download_liveportrait.py
set EXITCODE=%ERRORLEVEL%

echo.
if %EXITCODE% EQU 0 (
    echo ========================================
    echo  Done!
    echo  .env: GENERATOR_MODE=liveportrait
    echo  Test: .venv\Scripts\python.exe scripts\test_liveportrait.py
    echo ========================================
) else (
    echo Error %EXITCODE% - see data\liveportrait_download_log.txt
)

pause
exit /b %EXITCODE%
