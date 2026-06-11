"""
Smoke-тест InstantID keyframe: фото гостя -> фестивальный кадр с сохранением лица.
Не трогает сервер. Сохраняет PNG для визуальной оценки.

Запуск на FARM (модели на D:):
  set "PATH=C:\\Users\\user\\gigavibe\\.venv\\Lib\\site-packages\\torch\\lib;%PATH%"
  set "INSTANTID_BASE_DIR=D:\\gigavibe-models\\sdxl-base"
  set "INSTANTID_REPO_DIR=D:\\gigavibe-models\\InstantID"
  set "INSTANTID_ANTELOPE_ROOT=D:\\gigavibe-models\\insightface_antelope"
  set "HF_HOME=D:\\gigavibe-models\\hf-cache"
  .venv\\Scripts\\python.exe scripts\\test_keyframe_instantid.py --image data\\test_face.jpg
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys

sys.path.insert(0, str(ROOT))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default="data/test_face.jpg")
    ap.add_argument("--out", default="data/outputs/keyframe_test.png")
    ap.add_argument("--width", type=int, default=720)
    ap.add_argument("--height", type=int, default=1280)
    ap.add_argument("--steps", type=int, default=None)
    ap.add_argument("--ip-scale", type=float, default=None, help="identity strength 0..1")
    ap.add_argument("--cn-scale", type=float, default=None, help="controlnet keypoints 0..1")
    ap.add_argument("--prompt", default=None)
    ap.add_argument("--brand", action="store_true", help="use glossy-3D brand prompt (Seedance look)")
    args = ap.parse_args()

    import app.cuda_bootstrap  # noqa: F401
    import torch

    from app.config import settings

    if args.steps is not None:
        settings.instantid_steps = args.steps
    if args.ip_scale is not None:
        settings.instantid_ip_scale = args.ip_scale
    if args.cn_scale is not None:
        settings.instantid_controlnet_scale = args.cn_scale
    if args.brand:
        from app.prompts import KEYFRAME_BRAND_NEGATIVE_PROMPT, KEYFRAME_BRAND_PROMPT

        settings.instantid_prompt = KEYFRAME_BRAND_PROMPT
        settings.instantid_negative_prompt = KEYFRAME_BRAND_NEGATIVE_PROMPT
    if args.prompt is not None:
        settings.instantid_prompt = args.prompt

    from app.generators.keyframe_instantid import KeyframeInstantIDGenerator

    print("=== InstantID keyframe smoke test ===", flush=True)
    print(f"available: {KeyframeInstantIDGenerator.is_available()}", flush=True)
    if not KeyframeInstantIDGenerator.is_available():
        print("InstantID НЕ доступен — проверьте ControlNetModel/ip-adapter.bin/vendor pipeline", flush=True)
        return

    src = ROOT / args.image
    if not src.exists():
        print(f"Нет фото: {src}", flush=True)
        return
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)

    dev_id = int(getattr(settings, "instantid_device_id", 0))
    print(
        f"device=cuda:{dev_id}, steps={settings.instantid_steps}, "
        f"ip_scale={settings.instantid_ip_scale}, cn_scale={settings.instantid_controlnet_scale}",
        flush=True,
    )

    t0 = time.perf_counter()
    gen = KeyframeInstantIDGenerator()
    keyframe = gen.generate_keyframe(src, args.width, args.height)
    dt = time.perf_counter() - t0

    keyframe.save(out)
    if torch.cuda.is_available():
        peak = torch.cuda.max_memory_allocated(dev_id) / 1024**3
    else:
        peak = 0.0

    print("=== RESULT ===", flush=True)
    print(f"keyframe: {dt:.1f} s", flush=True)
    print(f"peak VRAM: {peak:.2f} GB", flush=True)
    print(f"saved: {out} ({out.stat().st_size // 1024} KB, {keyframe.size[0]}x{keyframe.size[1]})", flush=True)


if __name__ == "__main__":
    main()
