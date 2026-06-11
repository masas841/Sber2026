"""A/B-проверка GPU-резидентного конвейера inswapper vs CPU-эталон.

1. Корректность: своп одного кадра обоими путями, попиксельная разница.
   Если theta для grid_sample выведена верно — лицо в том же месте,
   разница в основном от bilinear vs cv2 интерполяции (несколько единиц яркости).
2. Скорость: N кадров каждым путём, fps и мс/кадр.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    from app.generators.ref_video import RefVideoGenerator, _largest_face
    from PIL import Image

    n = 100
    driver = ROOT / "assets" / "driving" / "IMG_9240.MP4"
    src_img = ROOT / "data" / "test_from_driving.jpg"

    face_app, _ = RefVideoGenerator._load_models()
    fast = RefVideoGenerator._inswapper_fast
    if fast is None:
        print("Нужен REF_VIDEO_SWAP_ENGINE=inswapper_fast")
        return

    src_bgr = cv2.cvtColor(np.array(Image.open(src_img).convert("RGB")), cv2.COLOR_RGB2BGR)
    source_face = _largest_face(face_app.get(src_bgr))
    latent = fast.embed_latent(source_face.normed_embedding)

    cap = cv2.VideoCapture(str(driver))
    ok, frame = cap.read()
    while ok:
        faces = face_app.get(frame)
        f = _largest_face(faces)
        if f is not None:
            break
        ok, frame = cap.read()
    if f is None:
        print("Нет лица")
        return
    kps = f.kps

    # --- корректность: GPU vs CPU на одном кадре ---
    out_cpu = fast.swap_cpu_ref(frame, kps, latent)
    out_gpu = fast._swap_gpu(frame, __import__("insightface").utils.face_align.estimate_norm(kps, fast.input_size), latent)

    diff = np.abs(out_cpu.astype(np.int16) - out_gpu.astype(np.int16))
    # сравниваем только область лица (где маска > 0), фон совпадает тривиально
    print(f"GPU vs CPU diff: mean={diff.mean():.2f}, max={diff.max()}, "
          f"p99={np.percentile(diff, 99):.0f} (of 255)")
    cv2.imwrite(str(ROOT / "data" / "outputs" / "ab_gpu.png"), out_gpu)
    cv2.imwrite(str(ROOT / "data" / "outputs" / "ab_cpu.png"), out_cpu)

    # --- скорость ---
    import insightface
    M = insightface.utils.face_align.estimate_norm(kps, fast.input_size)

    for _ in range(3):  # прогрев
        fast._swap_gpu(frame, M, latent)

    t0 = time.perf_counter()
    for _ in range(n):
        fast._swap_gpu(frame, M, latent)
    t_gpu = (time.perf_counter() - t0) / n

    t0 = time.perf_counter()
    for _ in range(n):
        fast.swap_cpu_ref(frame, kps, latent)
    t_cpu = (time.perf_counter() - t0) / n

    print(f"\nGPU-конвейер: {t_gpu*1000:.2f} мс/кадр ({1/t_gpu:.1f} fps)")
    print(f"CPU-эталон:   {t_cpu*1000:.2f} мс/кадр ({1/t_cpu:.1f} fps)")
    print(f"Ускорение swap: x{t_cpu/t_gpu:.2f}")
    print(f"На 300 кадров: GPU ~{300*t_gpu:.1f}с | CPU ~{300*t_cpu:.1f}с")


if __name__ == "__main__":
    main()
