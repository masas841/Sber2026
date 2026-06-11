"""
Smoke-тест Nano Banana: селфи → festival PNG.

  NANOBANANA_BACKEND=aitunnel + AITUNNEL_API_KEY  (без VPN, ~15–40с)
  NANOBANANA_BACKEND=quatarly + QUATARLY_API_KEY
  NANOBANANA_BACKEND=gemini + GEMINI_API_KEY
  NANOBANANA_BACKEND=proxy + NANOBANANA_API_KEY  (~100с)
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
    ap.add_argument("--image", default="data/test_face.png")
    ap.add_argument("--out", default="data/outputs/festival_nanobanana.png")
    ap.add_argument("--width", type=int, default=720)
    ap.add_argument("--height", type=int, default=1280)
    ap.add_argument("--show-prompt", action="store_true")
    args = ap.parse_args()

    from app.config import settings
    from app.generators.festival_nanobanana import FestivalNanobananaGenerator
    from app.guest_profile import analyze_guest_image, profile_to_dict
    from app.prompts import build_nanobanana_prompt

    src = ROOT / args.image
    if not src.exists():
        print(f"Нет фото: {src}")
        raise SystemExit(1)

    backend = FestivalNanobananaGenerator.backend()
    print(f"=== nanobanana test (backend={backend}) ===")
    print(f"available: {FestivalNanobananaGenerator.is_available()}")
    if not FestivalNanobananaGenerator.is_available():
        print(FestivalNanobananaGenerator.install_hint())
        raise SystemExit(1)

    profile = analyze_guest_image(src)
    prompt = build_nanobanana_prompt(profile)
    print(f"profile: {profile.label_ru()}")
    if args.show_prompt:
        print("--- prompt ---")
        print(prompt)

    out = ROOT / args.out
    t0 = time.perf_counter()
    FestivalNanobananaGenerator().generate(
        src,
        out,
        width=args.width,
        height=args.height,
        fps=30,
        duration_sec=10,
        guest_profile=profile,
    )
    sec = time.perf_counter() - t0
    print(f"PNG: {out} ({sec:.1f}s)")

    meta = {
        "profile": profile_to_dict(profile),
        "prompt": prompt,
        "nanobanana_sec": round(sec, 2),
    }
    meta_path = out.with_suffix(".json")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"meta: {meta_path}")


if __name__ == "__main__":
    main()
