"""Лёгкий InsightFace (buffalo_l) для профиля гостя без загрузки inswapper."""

from __future__ import annotations

import logging

from app.generators.ref_video import INSIGHTFACE_ROOT, _ensure_buffalo_l, _onnx_providers

logger = logging.getLogger(__name__)

_face_app = None


def get_face_app():
    """FaceAnalysis buffalo_l — только детекция/пол/возраст для селфи."""
    global _face_app
    if _face_app is not None:
        return _face_app

    from insightface.app import FaceAnalysis

    from app.config import settings

    _ensure_buffalo_l()
    dev_id = int(settings.ref_video_swap_device_id)
    providers = _onnx_providers(dev_id)
    ctx = dev_id if providers[0] != "CPUExecutionProvider" else -1
    if isinstance(providers[0], tuple):
        ctx = dev_id

    det_size = max(320, int(settings.guest_face_det_size))
    det_thresh = float(settings.guest_face_det_thresh)

    app = FaceAnalysis(
        name="buffalo_l",
        root=str(INSIGHTFACE_ROOT),
        providers=providers,
    )
    app.prepare(ctx_id=ctx, det_size=(det_size, det_size), det_thresh=det_thresh)
    _face_app = app
    logger.info(
        "face_analysis: buffalo_l ready (ctx_id=%s, det=%sx%s thresh=%.2f)",
        ctx,
        det_size,
        det_size,
        det_thresh,
    )
    return _face_app
