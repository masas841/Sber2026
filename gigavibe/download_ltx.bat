@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  GIGAvibe - загрузка LTX-Video
echo  ~15-25 GB -^> models\LTX-Video
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Создаю виртуальное окружение...
    python -m venv .venv
    if errorlevel 1 goto :error
    call .venv\Scripts\activate.bat
    echo [2/3] Устанавливаю зависимости...
    pip install -r requirements.txt
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
) else (
    call .venv\Scripts\activate.bat
)

set HF_HUB_DISABLE_SYMLINKS_WARNING=1

REM HF_TOKEN читается из .env внутри Python-скрипта

echo [3/3] Загрузка модели...
echo.
echo  В окне будет показано:
echo    - сколько GB скачано
echo    - скорость MB/s
echo    - число файлов
echo.
echo  Полный лог: data\ltx_download_log.txt
echo.

set PYTHONUNBUFFERED=1
.venv\Scripts\python.exe -u scripts\download_ltx.py
set EXITCODE=%ERRORLEVEL%

echo.
if %EXITCODE% EQU 0 (
    echo ========================================
    echo  Готово! models\LTX-Video
    echo  В .env: GENERATOR_MODE=ltx
    echo  Запуск: run.ps1
    echo ========================================
) else (
    echo ========================================
    echo  Ошибка. Код: %EXITCODE%
    echo  См. data\ltx_download_log.txt
    echo ========================================
    goto :error
)

pause
exit /b 0

:error
pause
exit /b 1
