"""Smoke-тест ref_video / LivePortrait."""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw

from app.config import settings
from app.generators.factory import get_generator


def _make_test_face(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (720, 1280), (40, 120, 200))
    draw = ImageDraw.Draw(img)
    draw.ellipse((220, 280, 500, 620), fill=(255, 220, 190))
    draw.ellipse((280, 400, 330, 450), fill=(60, 40, 30))
    draw.ellipse((390, 400, 440, 450), fill=(60, 40, 30))
    draw.arc((300, 480, 420, 560), 20, 160, fill=(120, 60, 60), width=4)
    img.save(path, format="JPEG", quality=92)


def main() -> None:
    src = ROOT / "data" / "d82b2cd44e90.mp4_snapshot_00.01.030.jpg"
    if not src.exists():
        src = ROOT / "data" / "test_from_driving.jpg"
    if not src.exists():
        src = ROOT / "data" / "test_face.jpg"
        _make_test_face(src)
    print("Source:", src.name)
    out = ROOT / "data" / "test_liveportrait.mp4"
    gen = get_generator()
    print("Generator:", gen.__class__.__name__)
    print("Driving:", settings.liveportrait_driving_path)
    print("Генерация...", flush=True)
    t0 = time.perf_counter()
    gen.generate(
        src,
        out,
        width=settings.video_width,
        height=settings.video_height,
        fps=settings.video_fps,
        duration_sec=settings.video_duration_sec,
    )
    elapsed = getattr(gen, "last_generation_sec", None) or (time.perf_counter() - t0)
    prov = getattr(gen, "last_onnx_provider", None)
    prov_s = f" ({prov})" if prov else ""
    print(f"Время генерации: {elapsed:.1f} с{prov_s}")
    print("OK:", out, f"({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
