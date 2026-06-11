"""
Генерация фонов киоска (без людей) в assets/fon/.

  .venv\\Scripts\\python.exe scripts\\generate_fon_backgrounds.py --count 10
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--out-dir", default="assets/fon")
    ap.add_argument("--width", type=int, default=720)
    ap.add_argument("--height", type=int, default=1280)
    ap.add_argument("--show-prompt", action="store_true")
    args = ap.parse_args()

    from app.aitunnel_image_client import generate_scene_image
    from app.config import settings
    from app.prompts import build_nanobanana_background_prompt

    api_key = (settings.aitunnel_api_key or "").strip()
    if not api_key:
        print("Нужен AITUNNEL_API_KEY в .env")
        raise SystemExit(1)

    prompt = build_nanobanana_background_prompt()
    if args.show_prompt:
        print("--- prompt ---")
        print(prompt)

    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== fon backgrounds x{args.count} ({args.width}x{args.height}) ===")
    meta: list[dict] = []
    t_all = time.perf_counter()

    for i in range(1, args.count + 1):
        variant_prompt = (
            f"{prompt}\n\nVariation {i} of {args.count}: unique layout, different hero shapes."
        )
        t0 = time.perf_counter()
        print(f"[{i}/{args.count}] generating…", flush=True)
        img = generate_scene_image(
            api_key=api_key,
            base_url=settings.aitunnel_api_base_url,
            model=settings.nanobanana_model,
            prompt=variant_prompt,
            aspect_ratio=settings.nanobanana_aspect_ratio,
            image_size=settings.nanobanana_image_size,
        )
        from PIL import Image

        if img.size != (args.width, args.height):
            img = img.resize((args.width, args.height), Image.Resampling.LANCZOS)

        out_path = out_dir / f"fon_{i:02d}.jpg"
        img.save(out_path, format="JPEG", quality=92, optimize=True)
        sec = time.perf_counter() - t0
        print(f"  saved {out_path.name} ({sec:.1f}s, {out_path.stat().st_size // 1024} KB)")
        meta.append({"file": out_path.name, "sec": round(sec, 2)})

    total = time.perf_counter() - t_all
    summary = {
        "count": args.count,
        "size": [args.width, args.height],
        "model": settings.nanobanana_model,
        "aspect_ratio": settings.nanobanana_aspect_ratio,
        "image_size": settings.nanobanana_image_size,
        "total_sec": round(total, 2),
        "files": meta,
        "prompt": prompt,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"done in {total:.1f}s -> {out_dir}")


if __name__ == "__main__":
    main()
