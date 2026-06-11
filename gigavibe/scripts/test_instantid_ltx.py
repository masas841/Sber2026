"""Smoke-test полного локального пайплайна InstantID keyframe -> LTX без веб-сервера."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default="data/test_face.jpg")
    ap.add_argument("--out", default="data/outputs/instantid_ltx_smoke.mp4")
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--height", type=int, default=None)
    ap.add_argument("--fps", type=int, default=None)
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--quality", default="fast")
    ap.add_argument("--brand", action="store_true")
    args = ap.parse_args()

    from app.config import settings
    from app.generators.ltx import LtxGenerator

    if args.brand:
        from app.prompts import (
            KEYFRAME_BRAND_NEGATIVE_PROMPT,
            KEYFRAME_BRAND_PROMPT,
            LTX_BRAND_NEGATIVE_PROMPT,
            LTX_BRAND_PROMPT,
        )

        settings.instantid_prompt = KEYFRAME_BRAND_PROMPT
        settings.instantid_negative_prompt = KEYFRAME_BRAND_NEGATIVE_PROMPT
        settings.ltx_prompt = LTX_BRAND_PROMPT
        settings.ltx_negative_prompt = LTX_BRAND_NEGATIVE_PROMPT

    settings.keyframe_mode = "instantid"
    settings.ltx_quality = args.quality

    image = Path(args.image)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    width = args.width or settings.video_width
    height = args.height or settings.video_height
    fps = args.fps or settings.video_fps
    duration = args.duration or min(float(settings.video_duration_sec), 2.0)

    print("=== InstantID -> LTX smoke test ===", flush=True)
    print(
        f"image={image}, out={out}, size={width}x{height}, fps={fps}, duration={duration}, "
        f"quality={settings.ltx_quality}, ltx_device={settings.ltx_device_id}, "
        f"instantid_device={settings.instantid_device_id}, keep_resident={settings.keyframe_keep_resident}",
        flush=True,
    )

    gen = LtxGenerator(
        model_id=settings.ltx_model_id,
        num_frames=settings.ltx_num_frames,
        num_inference_steps=settings.ltx_inference_steps,
        guidance_scale=settings.ltx_guidance_scale,
        distilled=settings.ltx_distilled,
        gguf_repo_file=settings.ltx_gguf_repo_file,
    )

    t0 = time.perf_counter()
    result = gen.generate(
        image,
        out,
        width=width,
        height=height,
        fps=fps,
        duration_sec=duration,
    )
    elapsed = time.perf_counter() - t0

    print("=== RESULT ===", flush=True)
    print(f"pipeline: {elapsed:.1f} s", flush=True)
    print(f"saved: {result.resolve()} ({result.stat().st_size // 1024} KB)", flush=True)

    _report_motion(result)


def _report_motion(video_path: Path) -> None:
    """Количественная оценка движения: средняя/мин/макс попарная разница соседних кадров.
    Низкое среднее и (особенно) много нулей подряд = «фриз»/растяжка дублей."""
    import cv2
    import numpy as np

    cap = cv2.VideoCapture(str(video_path))
    prev = None
    diffs: list[float] = []
    zero_pairs = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev is not None:
            d = float(np.mean(cv2.absdiff(gray, prev)))
            diffs.append(d)
            if d < 0.05:
                zero_pairs += 1
        prev = gray
    cap.release()

    if not diffs:
        print("motion: нет кадров для оценки", flush=True)
        return

    arr = np.array(diffs)
    print("=== MOTION ===", flush=True)
    print(
        f"кадров={len(diffs) + 1}, пар={len(diffs)}, "
        f"mean_diff={arr.mean():.2f}, min={arr.min():.2f}, max={arr.max():.2f}, "
        f"почти_статичных_пар(<0.05)={zero_pairs}",
        flush=True,
    )


if __name__ == "__main__":
    main()
