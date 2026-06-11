"""Сохранить один кадр ref_video для A/B: legacy vs rope_v1.

  set REF_VIDEO_PIPELINE=legacy
  python scripts/compare_refvideo_frame.py --out data/frame_legacy.png

  set REF_VIDEO_PIPELINE=rope_v1
  python scripts/compare_refvideo_frame.py --out data/frame_rope_v1.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, default=ROOT / "data" / "test_from_driving.jpg")
    p.add_argument("--out", type=Path, default=ROOT / "data" / "compare_frame.png")
    p.add_argument("--frame-index", type=int, default=0)
    args = p.parse_args()

    from app.config import settings
    from app.generators.ref_video import RefVideoGenerator

    gen = RefVideoGenerator()
    face_app, swapper = gen._load_models()
    src = cv2.imread(str(args.source))
    if src is None:
        raise SystemExit(f"Не открыть {args.source}")

    source_faces = face_app.get(src)
    from app.generators.ref_video import _largest_face

    source_face = _largest_face(source_faces)
    if source_face is None:
        raise SystemExit("Нет лица на source")

    from app.generators.ref_video import _pick_reference_mp4

    cap = cv2.VideoCapture(str(_pick_reference_mp4()))
    for _ in range(args.frame_index + 1):
        ok, frame = cap.read()
    cap.release()
    if not ok:
        raise SystemExit("Нет кадра в референсе")

    fast = RefVideoGenerator._inswapper_fast
    latent = fast.embed_latent(source_face.normed_embedding)
    bboxes, kpss = face_app.det_model.detect(frame, max_num=0, metric="default")
    areas = (bboxes[:, 2] - bboxes[:, 0]) * (bboxes[:, 3] - bboxes[:, 1])
    kps = kpss[int(__import__("numpy").argmax(areas))]
    out = fast.swap(frame, kps, latent)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(args.out), out)
    print(f"pipeline={settings.ref_video_pipeline} -> {args.out}", flush=True)


if __name__ == "__main__":
    main()
