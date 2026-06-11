@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  GIGAvibe - LivePortrait
echo  vendor\LivePortrait + .venv-liveportrait
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [0] Создаю .venv для киоска...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

set HF_HUB_DISABLE_SYMLINKS_WARNING=1
set PYTHONUNBUFFERED=1

echo Установка LivePortrait (git + venv + веса)...
echo Лог: data\liveportrait_download_log.txt
echo.

.venv\Scripts\python.exe -u scripts\download_liveportrait.py
set EXITCODE=%ERRORLEVEL%

echo.
if %EXITCODE% EQU 0 (
    echo ========================================
    echo  Готово!
    echo  .env: GENERATOR_MODE=liveportrait
    echo  Тест: .venv\Scripts\python.exe scripts\test_liveportrait.py
    echo ========================================
) else (
    echo Ошибка %EXITCODE% - см. data\liveportrait_download_log.txt
)

pause
exit /b %EXITCODE%
