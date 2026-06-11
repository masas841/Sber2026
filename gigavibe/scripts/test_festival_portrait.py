"""
Локальный тест festival_portrait (RTX 3060): селфи → glossy 3D PNG.

Перед первым запуском:
  - models/sdxl-base, models/InstantID, models/insightface_antelope (antelopev2)
  - vendor/instantid (pipeline)
  - pip install diffusers transformers insightface onnxruntime-gpu

Пример:
  copy .env.portrait-local .env
  .\\run.ps1
  .venv\\Scripts\\python.exe scripts\\test_festival_portrait.py --image data\\test_face.jpg
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys

sys.path.insert(0, str(ROOT))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default="data/test_face.jpg")
    ap.add_argument("--out", default="data/outputs/festival_portrait.png")
    ap.add_argument("--width", type=int, default=720)
    ap.add_argument("--height", type=int, default=1280)
    ap.add_argument("--show-prompt", action="store_true")
    args = ap.parse_args()

    import app.cuda_bootstrap  # noqa: F401

    from app.generators.festival_portrait import FestivalPortraitGenerator
    from app.guest_profile import analyze_guest_image, profile_to_dict
    from app.prompts import build_festival_portrait_prompt

    src = ROOT / args.image
    if not src.exists():
        print(f"Нет фото: {src}")
        return

    print("=== festival_portrait local test ===")
    print(f"available: {FestivalPortraitGenerator.is_available()}")
    if not FestivalPortraitGenerator.is_available():
        print(FestivalPortraitGenerator.install_hint())
        return

    t0 = time.perf_counter()
    profile = analyze_guest_image(src)
    profile_sec = time.perf_counter() - t0
    prompt, negative = build_festival_portrait_prompt(profile)
    print(f"profile ({profile_sec:.1f}s): {profile.label_ru()}")
    if args.show_prompt:
        print("--- prompt ---")
        print(prompt)
        print("--- negative ---")
        print(negative)

    out = ROOT / args.out
    t1 = time.perf_counter()
    FestivalPortraitGenerator().generate(
        src,
        out,
        width=args.width,
        height=args.height,
        fps=30,
        duration_sec=10,
        guest_profile=profile,
    )
    total_sec = time.perf_counter() - t1
    print(f"PNG: {out} ({total_sec:.1f}s)")

    meta = {
        "profile": profile_to_dict(profile),
        "prompt": prompt,
        "negative": negative,
        "instantid_sec": round(total_sec, 2),
    }
    meta_path = out.with_suffix(".json")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"meta: {meta_path}")
    print("Dolly-out на киоске — CSS (--dolly-duration), MP4 не нужен.")


if __name__ == "__main__":
    main()
