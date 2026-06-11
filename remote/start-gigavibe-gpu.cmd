@echo off
cd /d C:\Users\user\gigavibe
rem Обе RTX 3090: swap на cuda:0, GFPGAN на cuda:1 (см. REF_VIDEO_*_DEVICE_ID в .env)
set PATH=C:\Users\user\gigavibe\.venv\Lib\site-packages\torch\lib;%PATH%
set PYTHONUNBUFFERED=1
.venv\Scripts\python.exe -m app.main
