@echo off
cd /d C:\Users\user\gigavibe
set CUDA_VISIBLE_DEVICES=0
set PATH=C:\Users\user\gigavibe\.venv\Lib\site-packages\torch\lib;%PATH%
set KEYFRAME_MODE=instantid
set INSTANTID_BASE_DIR=D:\gigavibe-models\sdxl-base
set INSTANTID_REPO_DIR=D:\gigavibe-models\InstantID
set INSTANTID_ANTELOPE_ROOT=D:\gigavibe-models\insightface_antelope
set INSTANTID_PIPELINE_DIR=C:\Users\user\gigavibe\vendor\instantid
set HF_HOME=D:\gigavibe-models\hf-cache
.venv\Scripts\python.exe remote\test_keyframe.py
