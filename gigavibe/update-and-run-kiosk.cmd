@echo off
setlocal
cd /d "%~dp0"

echo [GIGAvibe] Updating from GitHub...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install\update-from-github.ps1"
if errorlevel 1 (
    echo [GIGAvibe] Update failed. Kiosk was not started.
    pause
    exit /b 1
)

echo [GIGAvibe] Starting kiosk...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-kiosk.ps1" -SkipUpdate
set "exitCode=%ERRORLEVEL%"
if not "%exitCode%"=="0" pause
exit /b %exitCode%
