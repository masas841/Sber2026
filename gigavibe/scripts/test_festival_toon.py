"""
Локальный тест festival_toon: селфи → Disney/Pixar 3D PNG (PuLID-FLUX fp8).

  git clone vendor/pulid (scripts/vendor-pulid.ps1)
  pip install optimum-quanto timm ftfy
  .venv\\Scripts\\python.exe scripts\\download_festival_toon_models.py
  .venv\\Scripts\\python.exe scripts\\test_festival_toon.py --image data\\test_face.png
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys

sys.path.insert(0, str(ROOT))

# PuLID ищет models/ относительно cwd
os.chdir(ROOT)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default="data/test_face.png")
    ap.add_argument("--out", default="data/outputs/festival_toon.png")
    ap.add_argument("--width", type=int, default=720)
    ap.add_argument("--height", type=int, default=1280)
    ap.add_argument("--show-prompt", action="store_true")
    args = ap.parse_args()

    import app.cuda_bootstrap  # noqa: F401

    from app.generators.festival_toon import FestivalToonGenerator
    from app.prompts import build_festival_toon_prompt

    src = ROOT / args.image
    if not src.exists():
        print(f"Нет фото: {src}")
        raise SystemExit(1)

    print("=== festival_toon local test (PuLID-FLUX fp8) ===")
    print(f"cwd: {ROOT}")
    print(f"available: {FestivalToonGenerator.is_available()}")
    if not FestivalToonGenerator.is_available():
        print(FestivalToonGenerator.install_hint())
        raise SystemExit(1)

    prompt, negative = build_festival_toon_prompt(None)
    if args.show_prompt:
        print("--- prompt ---")
        print(prompt)
        print("--- negative ---")
        print(negative)

    out = ROOT / args.out
    t0 = time.perf_counter()
    FestivalToonGenerator().generate(
        src,
        out,
        width=args.width,
        height=args.height,
        fps=30,
        duration_sec=10,
    )
    sec = time.perf_counter() - t0
    print(f"PNG: {out} ({sec:.1f}s)")

    meta = {
        "prompt": prompt,
        "negative": negative,
        "pulid_flux_sec": round(sec, 2),
    }
    meta_path = out.with_suffix(".json")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"meta: {meta_path}")


if __name__ == "__main__":
    main()
