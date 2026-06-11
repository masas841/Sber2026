"""Профайлер пер-кадрового конвейера свопа: разбивает время на под-этапы,
чтобы понять, где реально уходит время (и в чём выигрывает Rope).

Этапы на кадр:
  detect      — поиск лица (lean: только det_10g)
  align+blob  — norm_crop2 (cv2.warpAffine на CPU) + blobFromImage
  infer       — ONNX inswapper (GPU, io-binding)
  paste       — обратный warpAffine + GaussianBlur вклейка (CPU)
  (между этапами — копии numpy↔GPU)

Rope держит ВСЁ это на GPU как torch-тензоры → нет CPU-warp/blur и копий.
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
    from app.config import settings
    from app.generators.ref_video import RefVideoGenerator, _largest_face
    from PIL import Image

    n_frames = 120
    driver = ROOT / "assets" / "driving" / "IMG_9240.MP4"
    src_img = ROOT / "data" / "test_from_driving.jpg"

    face_app, swapper = RefVideoGenerator._load_models()
    fast = RefVideoGenerator._inswapper_fast
    if fast is None:
        print("Нужен REF_VIDEO_SWAP_ENGINE=inswapper_fast")
        return

    src_bgr = cv2.cvtColor(np.array(Image.open(src_img).convert("RGB")), cv2.COLOR_RGB2BGR)
    source_face = _largest_face(face_app.get(src_bgr))
    latent = fast.embed_latent(source_face.normed_embedding)

    from insightface.utils import face_align

    cap = cv2.VideoCapture(str(driver))
    det_size = (640, 640)
    t = {"detect": 0.0, "align_blob": 0.0, "infer": 0.0, "paste": 0.0}
    count = 0

    # прогрев (первый кадр — компиляция cudnn)
    ok, warm = cap.read()
    if ok:
        face_app.det_model.detect(warm, max_num=0, metric="default", input_size=det_size)

    while count < n_frames:
        ok, frame = cap.read()
        if not ok:
            break

        t0 = time.perf_counter()
        bboxes, kpss = face_app.det_model.detect(frame, max_num=0, metric="default", input_size=det_size)
        t1 = time.perf_counter()
        if bboxes is None or len(bboxes) == 0:
            continue
        areas = (bboxes[:, 2] - bboxes[:, 0]) * (bboxes[:, 3] - bboxes[:, 1])
        kps = kpss[int(np.argmax(areas))]

        t2 = time.perf_counter()
        aimg, M = face_align.norm_crop2(frame, kps, fast.input_size)
        blob = cv2.dnn.blobFromImage(
            aimg, 1.0 / fast.input_std, (fast.input_size, fast.input_size),
            (fast.input_mean,) * 3, swapRB=True,
        )
        t3 = time.perf_counter()
        pred = fast._run(blob, latent)[0]
        t4 = time.perf_counter()
        img_fake = np.transpose(pred, (1, 2, 0))
        img_fake = np.clip(img_fake * 255.0, 0, 255).astype(np.uint8)
        bgr_fake = cv2.cvtColor(img_fake, cv2.COLOR_RGB2BGR)
        _ = fast._paste_back(frame, bgr_fake, M)
        t5 = time.perf_counter()

        t["detect"] += t1 - t0
        t["align_blob"] += t3 - t2
        t["infer"] += t4 - t3
        t["paste"] += t5 - t4
        count += 1

    cap.release()
    if count == 0:
        print("Нет кадров с лицом")
        return

    total = sum(t.values())
    print(f"\nКадров: {count}, разрешение: {frame.shape[1]}x{frame.shape[0]}")
    print(f"{'этап':<14}{'мс/кадр':>10}{'доля':>8}")
    for k in ("detect", "align_blob", "infer", "paste"):
        ms = t[k] / count * 1000
        print(f"{k:<14}{ms:>10.2f}{t[k]/total*100:>7.0f}%")
    print(f"{'ИТОГО':<14}{total/count*1000:>10.2f}{100:>7}%")
    print(f"\nПропускная способность: {count/total:.1f} fps")
    print(f"На 300 кадров (10с@30fps): ~{300*total/count:.1f}с")


if __name__ == "__main__":
    main()
