"""Smoke-тест инлайн-restore: detect kps на одном кадре → restore_frame_with_landmarks.

Проверяет весь путь (align_warp_face по kps + gfpgan + paste) ДО рестарта прода.
Сохраняет before/after для визуальной проверки.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    from app.face_restore import _get_restorer, restore_frame_with_landmarks
    from app.generators.ref_video import RefVideoGenerator, _largest_face

    src = Path("assets/driving/IMG_9240.MP4")
    cap = cv2.VideoCapture(str(src))
    cap.set(cv2.CAP_PROP_POS_FRAMES, 30)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise SystemExit(f"Не прочитать кадр из {src}")

    face_app, _ = RefVideoGenerator._load_models()
    face = _largest_face(face_app.get(frame))
    if face is None:
        raise SystemExit("Лицо не найдено на кадре")
    kps = face.kps
    print("kps:\n", kps)

    restorer = _get_restorer()
    # Прогрев + замер.
    out = restore_frame_with_landmarks(frame, kps, restorer, 0.5)
    t0 = time.perf_counter()
    for _ in range(5):
        out = restore_frame_with_landmarks(frame, kps, restorer, 0.5)
    dt = (time.perf_counter() - t0) / 5.0
    print(f"inline-restore: {dt*1000:.1f} ms/frame ({1/dt:.1f} fps)")
    print("out shape:", out.shape, "dtype:", out.dtype)

    diff = np.abs(out.astype(np.int16) - frame.astype(np.int16))
    print(f"diff vs original: mean={diff.mean():.2f} max={int(diff.max())}")

    Path("data/outputs").mkdir(parents=True, exist_ok=True)
    cv2.imwrite("data/outputs/inline_restore_before.png", frame)
    cv2.imwrite("data/outputs/inline_restore_after.png", out)
    print("saved data/outputs/inline_restore_{before,after}.png")


if __name__ == "__main__":
    main()
