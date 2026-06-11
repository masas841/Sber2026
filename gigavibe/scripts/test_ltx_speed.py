"""
Замер скорости/VRAM LTX без запуска FastAPI (не трогает production ref_video).

Запуск на FARM:
  set PATH=C:\\Users\\user\\gigavibe\\.venv\\Lib\\site-packages\\torch\\lib;%PATH%
  .venv\\Scripts\\python.exe scripts\\test_ltx_speed.py --strategy full --steps 20 --frames 25

Печатает: время загрузки пайплайна, время генерации, пиковую VRAM, путь к выходному mp4.
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
    ap.add_argument("--strategy", default=None, help="full|model_offload|sequential_offload (override .env)")
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--frames", type=int, default=25)
    ap.add_argument("--width", type=int, default=512)
    ap.add_argument("--height", type=int, default=704)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--duration", type=float, default=1.0)
    ap.add_argument("--image", default="data/test_face.jpg")
    ap.add_argument("--out", default="data/outputs/ltx_speed_test.mp4")
    args = ap.parse_args()

    import app.cuda_bootstrap  # noqa: F401
    import torch

    from app.config import settings

    if args.strategy:
        settings.ltx_vram_strategy = args.strategy
    settings.ltx_inference_steps = args.steps
    settings.ltx_num_frames = args.frames
    # Тестовое разрешение через caps пресета — переопределим напрямую в генераторе ниже.

    dev_id = int(settings.ltx_device_id)
    strategy = settings.ltx_vram_strategy

    from app.generators.ltx import LtxGenerator

    if not LtxGenerator.is_available():
        print("LTX недоступен (torch/cuda)")
        return

    src = ROOT / args.image
    if not src.exists():
        print(f"Нет входного фото: {src}")
        return
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)

    def _safe(fn, default=0.0):
        try:
            return fn()
        except Exception:
            return default

    if torch.cuda.is_available():
        _safe(lambda: torch.cuda.reset_peak_memory_stats(dev_id))

    gen = LtxGenerator(
        model_id=settings.ltx_model_id,
        num_frames=args.frames,
        num_inference_steps=args.steps,
        guidance_scale=settings.ltx_guidance_scale or 3.5,
        distilled=settings.ltx_distilled,
        gguf_repo_file=settings.ltx_gguf_repo_file,
    )

    print(f"=== LTX speed test: strategy={strategy}, steps={args.steps}, frames={args.frames} ===", flush=True)

    t_load0 = time.perf_counter()
    gen._load_pipeline()
    t_load = time.perf_counter() - t_load0
    print(f"load_pipeline: {t_load:.1f} s", flush=True)

    if torch.cuda.is_available():
        mem_after_load = _safe(lambda: torch.cuda.memory_allocated(dev_id) / 1024**3)
        print(f"VRAM allocated after load: {mem_after_load:.2f} GB", flush=True)

    t_gen0 = time.perf_counter()
    gen.generate(
        src,
        out,
        width=args.width,
        height=args.height,
        fps=args.fps,
        duration_sec=args.duration,
    )
    t_gen = time.perf_counter() - t_gen0

    peak = 0.0
    if torch.cuda.is_available():
        peak = torch.cuda.max_memory_allocated(dev_id) / 1024**3

    print("=== RESULT ===", flush=True)
    print(f"strategy={strategy}", flush=True)
    print(f"generate: {t_gen:.1f} s", flush=True)
    print(f"peak VRAM: {peak:.2f} GB", flush=True)
    print(f"output: {out} ({out.stat().st_size // 1024} KB)" if out.exists() else "output: MISSING", flush=True)


if __name__ == "__main__":
    main()
