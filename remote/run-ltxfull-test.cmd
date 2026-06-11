@echo off
cd /d C:\Users\user\gigavibe
set CUDA_VISIBLE_DEVICES=0
set PATH=C:\Users\user\gigavibe\.venv\Lib\site-packages\torch\lib;%PATH%
set GENERATOR_MODE=ltx
set KEYFRAME_MODE=instantid
set LTX_MODEL_DIR=D:\gigavibe-models\LTX-Video
set INSTANTID_BASE_DIR=D:\gigavibe-models\sdxl-base
set INSTANTID_REPO_DIR=D:\gigavibe-models\InstantID
set INSTANTID_ANTELOPE_ROOT=D:\gigavibe-models\insightface_antelope
set INSTANTID_PIPELINE_DIR=C:\Users\user\gigavibe\vendor\instantid
set HF_HOME=D:\gigavibe-models\hf-cache
set LTX_GGUF_REPO_FILE=
set LTX_QUALITY=high
set LTX_NUM_FRAMES=257
set LTX_SEQUENTIAL_OFFLOAD=false
.venv\Scripts\python.exe remote\test_ltx_full.py
