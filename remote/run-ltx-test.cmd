@echo off
REM Тест LTX без веб-сервера. Модель на D:, GPU0, 257 кадров (>=250), без GGUF.
cd /d C:\Users\user\gigavibe
set CUDA_VISIBLE_DEVICES=0
set PATH=C:\Users\user\gigavibe\.venv\Lib\site-packages\torch\lib;%PATH%
set GENERATOR_MODE=ltx
set LTX_MODEL_DIR=D:\gigavibe-models\LTX-Video
set HF_HOME=D:\gigavibe-models\hf-cache
set LTX_GGUF_REPO_FILE=
set LTX_QUALITY=high
set LTX_NUM_FRAMES=257
set LTX_SEQUENTIAL_OFFLOAD=false
.venv\Scripts\python.exe scripts\test_ltx.py
