from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _run_generate(face_restore: bool, output_name: str) -> Path:
    os.environ["REF_VIDEO_FACE_RESTORE"] = "true" if face_restore else "false"
    # Важно: импорт после env override, Settings читает env при импорте app.config.
    from app.config import settings
    from app.generators.factory import get_generator

    # На случай повторного вызова в одном процессе меняем уже созданный Settings явно.
    settings.ref_video_face_restore = face_restore
    src = ROOT / "data" / "test_from_driving.jpg"
    if not src.exists():
        src = ROOT / "data" / "test_face.jpg"
    out = ROOT / "data" / output_name
    gen = get_generator()
    t0 = time.perf_counter()
    gen.generate(
        src,
        out,
        width=settings.video_width,
        height=settings.video_height,
        fps=settings.video_fps,
        duration_sec=settings.video_duration_sec,
    )
    wall = time.perf_counter() - t0
    print(
        f"{output_name}: wall={wall:.1f}s, gen.last={getattr(gen, 'last_generation_sec', None)}, "
        f"inline={getattr(gen, 'last_inline_restored', None)}, "
        f"restore_sec={getattr(gen, 'last_restore_sec', None)}, "
        f"strategy={getattr(gen, 'last_restore_strategy', None)}",
        flush=True,
    )
    return out


def _extract_frame(video: Path, frame_name: str, at_sec: float = 2.0) -> np.ndarray:
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {video}")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(int(round(at_sec * fps)), 0))
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"cannot read frame from {video}")
    cv2.imwrite(str(ROOT / "data" / frame_name), frame)
    return frame


def _label(img: np.ndarray, text: str) -> np.ndarray:
    out = img.copy()
    cv2.rectangle(out, (0, 0), (out.shape[1], 54), (0, 0, 0), -1)
    cv2.putText(out, text, (18, 36), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
    return out


def main() -> None:
    no_restore = _run_generate(False, "ab_refvideo_no_restore.mp4")
    with_restore = _run_generate(True, "ab_refvideo_inline_residual.mp4")
    a = _extract_frame(no_restore, "ab_refvideo_no_restore_f2.jpg")
    b = _extract_frame(with_restore, "ab_refvideo_inline_residual_f2.jpg")
    h = min(a.shape[0], b.shape[0])
    w = min(a.shape[1], b.shape[1])
    a = _label(a[:h, :w], "A: swap only / no GFPGAN")
    b = _label(b[:h, :w], "B: inline residual GFPGAN every 3")
    sheet = np.concatenate([a, b], axis=1)
    out = ROOT / "data" / "ab_refvideo_restore_sheet.jpg"
    cv2.imwrite(str(out), sheet)
    print(f"A/B sheet: {out}", flush=True)


if __name__ == "__main__":
    main()
