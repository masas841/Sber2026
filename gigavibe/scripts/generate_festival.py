"""Генерация LTX с фестивальным промптом (без веб-сервера)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw

from app.config import settings
from app.generators.ltx import LtxGenerator, _round_vae, _snap_frames
from app.prompts import FESTIVAL_PROMPT, NEGATIVE_PROMPT

photo = ROOT / "data" / "test_photo.jpg"
if not photo.exists():
    photo.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (800, 1200), (120, 220, 180))
    ImageDraw.Draw(img).ellipse([200, 300, 600, 900], fill=(255, 200, 220))
    img.save(photo)

out = ROOT / "data" / "outputs" / "festival_prompt.mp4"
out.parent.mkdir(parents=True, exist_ok=True)

gen = LtxGenerator(
    model_id=settings.ltx_model_id,
    num_frames=settings.ltx_num_frames,
    num_inference_steps=settings.ltx_inference_steps,
    guidance_scale=settings.ltx_guidance_scale,
    distilled=settings.ltx_distilled,
    gguf_repo_file=settings.ltx_gguf_repo_file,
)

print("Промпт:", FESTIVAL_PROMPT[:80], "...")
print("loading model...")
pipe = gen._load_pipeline()

import torch
from diffusers.utils import export_to_video

from app.video_encode import ensure_browser_mp4

width, height, fps = 544, 960, 24
duration_sec = 5.0

image = gen.load_and_fit(photo, width, height)
gen_w = _round_vae(min(width, 768))
gen_h = _round_vae(min(height, 1344))
if gen_h * gen_w > 768 * 512:
    scale = (768 * 512 / (gen_h * gen_w)) ** 0.5
    gen_w = _round_vae(int(gen_w * scale))
    gen_h = _round_vae(int(gen_h * scale))
image = image.resize((gen_w, gen_h), Image.Resampling.LANCZOS)
num_frames = min(_snap_frames(max(int(fps * duration_sec), 17)), gen.num_frames)

print(f"generating {gen_w}x{gen_h}, {num_frames} frames...")
g = torch.Generator(device="cpu").manual_seed(2026)
result = pipe(
    image=image,
    prompt=FESTIVAL_PROMPT,
    negative_prompt=NEGATIVE_PROMPT,
    width=gen_w,
    height=gen_h,
    num_frames=num_frames,
    frame_rate=fps,
    num_inference_steps=gen.num_inference_steps,
    guidance_scale=gen.guidance_scale,
    decode_timestep=0.08,
    decode_noise_scale=0.06,
    generator=g,
    output_type="pil",
)
frames = result.frames[0]
gen._write_output_from_frames(frames, out, width, height, fps, duration_sec)
ensure_browser_mp4(out, fps)
print("OK", out, out.stat().st_size, "bytes")
