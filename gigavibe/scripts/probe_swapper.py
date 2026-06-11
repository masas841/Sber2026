"""Проверка файла face-swap (inswapper_128/512) ДО прода.

Проверяет:
  1) ONNX грузится, реальный input shape (ожидаем NxCx512x512 для 512-модели),
  2) наличие инициализатора 'emap' — ключевой признак настоящего inswapper
     (фейки/апскейлы 128 часто без него либо с input 128),
  3) тестовый своп на одном кадре через InsightFace model_zoo (без падения).

Запуск (на FARM):
  python scripts/probe_swapper.py --model D:\\gigavibe-models\\inswapper_512.onnx \
      --src data\\test_face.jpg --ref assets\\driving\\IMG_9240.MP4 --out data\\outputs\\swap512_probe.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="путь к inswapper .onnx")
    ap.add_argument("--src", default="data/test_face.jpg", help="фото-источник лица")
    ap.add_argument("--ref", default="assets/driving/IMG_9240.MP4", help="видео/фото-цель")
    ap.add_argument("--out", default="data/outputs/swap_probe.png")
    ap.add_argument("--device", type=int, default=0)
    args = ap.parse_args()

    model_path = Path(args.model)
    print("=== SWAPPER PROBE ===", flush=True)
    print(f"model: {model_path}", flush=True)
    if not model_path.exists():
        print("FAIL: файл не найден", flush=True)
        sys.exit(2)
    print(f"size: {model_path.stat().st_size / 1e6:.1f} MB", flush=True)

    # 1) + 2) Статический разбор ONNX-графа
    import onnx

    model = onnx.load(str(model_path))
    inputs = model.graph.input
    print("--- inputs ---", flush=True)
    for inp in inputs:
        dims = [d.dim_value if d.dim_value > 0 else "?" for d in inp.type.tensor_type.shape.dim]
        print(f"  {inp.name}: {dims}", flush=True)

    init_names = {i.name for i in model.graph.initializer}
    has_emap = "emap" in init_names
    print(f"emap initializer present: {has_emap}", flush=True)

    # Определяем заявленный размер картинки из входа "target" (NCHW)
    img_size = None
    for inp in inputs:
        dims = [d.dim_value for d in inp.type.tensor_type.shape.dim]
        if len(dims) == 4 and dims[2] == dims[3] and dims[2] > 0:
            img_size = dims[2]
    print(f"detected input image size: {img_size}", flush=True)

    if not has_emap:
        print(
            "WARN: нет 'emap' — это нетипично для официального inswapper. "
            "Высокий риск, что файл не настоящий inswapper (фейк/иная модель).",
            flush=True,
        )

    # 3) Боевая проверка через InsightFace + реальный своп одного кадра
    import cv2
    import numpy as np
    from PIL import Image

    from app.generators.ref_video import (
        INSIGHTFACE_ROOT,
        _ensure_buffalo_l,
        _largest_face,
        _onnx_providers,
    )

    _ensure_buffalo_l()
    providers = _onnx_providers(args.device)

    import insightface
    from insightface.app import FaceAnalysis

    face_app = FaceAnalysis(name="buffalo_l", root=str(INSIGHTFACE_ROOT), providers=providers)
    ctx = args.device if providers and providers[0] != "CPUExecutionProvider" else -1
    face_app.prepare(ctx_id=ctx, det_size=(640, 640), det_thresh=0.4)

    swapper = insightface.model_zoo.get_model(str(model_path), providers=providers)
    # Реальный размер, который использует InsightFace (важнее, чем заявленный в графе)
    print(f"insightface swapper.input_size: {getattr(swapper, 'input_size', None)}", flush=True)

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
            print("FAIL: не прочитать первый кадр ref-видео", flush=True)
            sys.exit(3)
    else:
        target_bgr = cv2.cvtColor(np.array(Image.open(ref_path).convert("RGB")), cv2.COLOR_RGB2BGR)

    target_face = _largest_face(face_app.get(target_bgr))
    if target_face is None:
        print("FAIL: на ref не найдено лицо", flush=True)
        sys.exit(3)

    result = swapper.get(target_bgr, target_face, src_face, paste_back=True)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), result)

    # Размер области лица в кадре-цели — чтобы понять, есть ли апскейл свопа
    fb = target_face.bbox
    face_px = int(min(fb[2] - fb[0], fb[3] - fb[1]))
    print("=== RESULT ===", flush=True)
    print(f"face bbox short side: {face_px}px, swapper img_size: {img_size}", flush=True)
    if img_size and face_px:
        ratio = face_px / img_size
        verdict = "апскейл свопа (мыло вероятно)" if ratio > 1.1 else "своп ≥ лица (мыла мало)"
        print(f"face/{img_size} = {ratio:.2f} → {verdict}", flush=True)
    print(f"saved: {out.resolve()}", flush=True)


if __name__ == "__main__":
    main()
