"""Быстрый тест LTX без веб-сервера."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw

photo = ROOT / "data" / "test_photo.jpg"
if not photo.exists():
    photo.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (800, 1200), (120, 220, 180))
    ImageDraw.Draw(img).ellipse([200, 300, 600, 900], fill=(255, 200, 220))
    img.save(photo)

out = ROOT / "data" / "outputs" / "ltx_test.mp4"
out.parent.mkdir(parents=True, exist_ok=True)

from app.generators.ltx import LtxGenerator

from app.config import settings

gen = LtxGenerator(
    model_id=settings.ltx_model_id,
    num_frames=settings.ltx_num_frames,
    num_inference_steps=settings.ltx_inference_steps,
    guidance_scale=settings.ltx_guidance_scale,
    distilled=False,
    gguf_repo_file=settings.ltx_gguf_repo_file,
)
print("loading model...")
gen._load_pipeline()
print("generating...")
gen.generate(
    photo,
    out,
    width=settings.video_width,
    height=settings.video_height,
    fps=settings.video_fps,
    duration_sec=settings.video_duration_sec,
)
print("OK", out, out.stat().st_size)
