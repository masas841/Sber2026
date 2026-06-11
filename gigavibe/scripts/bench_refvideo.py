"""Замер разбивки времени ref_video: холодный старт (загрузка моделей) vs
горячий прогон (модели уже резидентны, как в production-киоске).

Прогоняет generate() ДВАЖДЫ в одном процессе:
  run #1 — холодный: загрузка buffalo_l + swapper + цикл + кодирование
  run #2 — горячий:  модели в кэше cls._, меряем реальный цикл+кодирование

Разница (cold - hot) ≈ время загрузки моделей, которого в проде нет на каждый ролик.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import settings
from app.generators.factory import get_generator


def main() -> None:
    src = ROOT / "data" / "test_from_driving.jpg"
    if not src.exists():
        src = ROOT / "data" / "test_face.jpg"
    out = ROOT / "data" / "bench_refvideo.mp4"
    gen = get_generator()
    print("Generator:", gen.__class__.__name__, flush=True)
    print(
        "Engine:", settings.ref_video_swap_engine,
        "| lean:", settings.ref_video_lean_detect,
        "| threaded:", settings.ref_video_threaded_read,
        "| inline_restore:", settings.ref_video_inline_restore,
        "| restore_workers:", settings.ref_video_restore_workers,
        "| serialize_jobs:", settings.ref_video_serialize_jobs,
        "| swap_workers:", settings.ref_video_swap_workers,
        "| restore_every_n:", settings.ref_video_restore_every_n,
        "| fast_model:", settings.inswapper_fast_model_path,
        "| pipeline:", settings.ref_video_pipeline,
        "| diff_amount:", settings.ref_video_diff_amount,
        flush=True,
    )

    times = []
    for i in (1, 2):
        t0 = time.perf_counter()
        gen.generate(
            src, out,
            width=settings.video_width,
            height=settings.video_height,
            fps=settings.video_fps,
            duration_sec=settings.video_duration_sec,
        )
        dt = getattr(gen, "last_generation_sec", None) or (time.perf_counter() - t0)
        restore_sec = getattr(gen, "last_restore_sec", None)
        restore_strategy = getattr(gen, "last_restore_strategy", None)
        inline_done = getattr(gen, "last_inline_restored", False)
        wall = time.perf_counter() - t0
        times.append(wall)
        tag = "COLD (с загрузкой моделей)" if i == 1 else "HOT (модели резидентны)"
        restore_part = (
            f", inline_restore={restore_sec:.1f}s"
            if inline_done and restore_sec is not None
            else f", inline_restore={inline_done}"
        )
        stages = getattr(gen, "last_stage_timings", None) or {}
        stage_part = f", stages={stages}" if stages else ""
        print(
            f"run #{i} {tag}: wall={wall:.1f}s, gen.last={dt:.1f}s{restore_part}{stage_part}, "
            f"restore_strategy={restore_strategy}",
            flush=True,
        )

    if len(times) == 2:
        print(f"\n=== РАЗБИВКА ===", flush=True)
        print(f"Загрузка моделей (cold-hot): ~{times[0]-times[1]:.1f}s", flush=True)
        print(f"Реальный прогон в проде (hot): ~{times[1]:.1f}s", flush=True)


if __name__ == "__main__":
    main()
