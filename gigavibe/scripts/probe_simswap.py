"""Проверка SimSwap-512 ДО прода: входы ONNX, корректность нормализации, тестовый своп.

Запуск (на FARM):
  python scripts/probe_simswap.py \
      --model D:\\gigavibe-models\\simswap_512_beta.onnx \
      --arcface D:\\gigavibe-models\\simswap_arcface.onnx \
      --src data\\test_face.jpg --ref assets\\driving\\IMG_9240.MP4 \
      --out data\\outputs\\simswap_probe.png

Если выход «мусорный» (цветной шум / инверсия) — перебрать нормализацию:
  --mean 0.5 --std 0.5   (частый вариант для SimSwap)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="simswap_512 .onnx")
    ap.add_argument("--arcface", required=True, help="arcface .onnx (identity-энкодер)")
    ap.add_argument("--src", default="data/test_face.jpg")
    ap.add_argument("--ref", default="assets/driving/IMG_9240.MP4")
    ap.add_argument("--out", default="data/outputs/simswap_probe.png")
    ap.add_argument("--device", type=int, default=0)
    ap.add_argument("--mean", type=float, default=0.0)
    ap.add_argument("--std", type=float, default=1.0)
    args = ap.parse_args()

    import cv2
    import numpy as np
    import onnx
    from PIL import Image

    print("=== SIMSWAP PROBE ===", flush=True)
    for label, p in (("model", args.model), ("arcface", args.arcface)):
        path = Path(p)
        if not path.exists():
            print(f"FAIL: {label} не найден: {path}", flush=True)
            sys.exit(2)
        print(f"{label}: {path} ({path.stat().st_size / 1e6:.1f} MB)", flush=True)

    # Разбор входов SimSwap-графа
    model = onnx.load(args.model)
    print("--- simswap inputs ---", flush=True)
    for inp in model.graph.input:
        dims = [d.dim_value if d.dim_value > 0 else "?" for d in inp.type.tensor_type.shape.dim]
        print(f"  {inp.name}: {dims}", flush=True)

    from app.generators.ref_video import (
        INSIGHTFACE_ROOT,
        _ensure_buffalo_l,
        _largest_face,
        _onnx_providers,
    )
    from app.generators.simswap import SimSwapEngine

    _ensure_buffalo_l()
    providers = _onnx_providers(args.device)

    from insightface.app import FaceAnalysis

    face_app = FaceAnalysis(name="buffalo_l", root=str(INSIGHTFACE_ROOT), providers=providers)
    ctx = args.device if providers and providers[0] != "CPUExecutionProvider" else -1
    face_app.prepare(ctx_id=ctx, det_size=(640, 640), det_thresh=0.4)

    engine = SimSwapEngine(Path(args.model), Path(args.arcface), providers)
    engine.input_mean = args.mean
    engine.input_std = args.std

    src_bgr = cv2.cvtColor(np.array(Image.open(args.src).convert("RGB")), cv2.COLOR_RGB2BGR)
    src_face = _largest_face(face_app.get(src_bgr))
    if src_face is None:
        print("FAIL: на src не найдено лицо", flush=True)
        sys.exit(3)

    ref_path = Path(args.ref)
    if ref_path.suffix.lower() in {".mp4", ".mov", ".avi"}:
        cap = cv2.VideoCapture(str(ref_path))
        ok, target_bgr = cap.read()
        cap.release()
        if not ok:
            print("FAIL: не прочитать кадр ref-видео", flush=True)
            sys.exit(3)
    else:
        target_bgr = cv2.cvtColor(np.array(Image.open(ref_path).convert("RGB")), cv2.COLOR_RGB2BGR)

    target_face = _largest_face(face_app.get(target_bgr))
    if target_face is None:
        print("FAIL: на ref не найдено лицо", flush=True)
        sys.exit(3)

    identity = engine.embed_identity(src_bgr, src_face.kps)
    print(f"identity vector: shape={identity.shape}, norm={float(np.linalg.norm(identity)):.3f}", flush=True)

    result = engine.swap(target_bgr, target_face.kps, identity)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), result)

    # Грубая проверка «не мусор»: дисперсия и средняя яркость в разумных пределах
    gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
    print("=== RESULT ===", flush=True)
    print(
        f"out mean={gray.mean():.1f}, std={gray.std():.1f}, "
        f"mean/std={args.mean}/{args.std}",
        flush=True,
    )
    print(f"saved: {out.resolve()}", flush=True)
    print("Проверьте файл визуально: лицо должно быть гостя, без цветного шума/инверсии.", flush=True)


if __name__ == "__main__":
    main()
