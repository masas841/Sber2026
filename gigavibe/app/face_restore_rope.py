"""Restore для rope_v1: GFPGAN ONNX 512 + diff-paste (как Rope, без facexlib на полный кадр)."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

import numpy as np

logger = logging.getLogger(__name__)
_onnx_restore_lock = threading.Lock()

if TYPE_CHECKING:
    from app.generators.gfpgan_onnx import GfpganOnnxEngine


def restore_face_512_bgr_tensor(
    face_bgr_512,
    engine: "GfpganOnnxEngine",
    blend: float = 0.5,
):
    """(1,3,512,512) BGR float → restored BGR float."""
    return engine.restore_blend_bgr(face_bgr_512, blend=blend)


def restore_frame_onnx_with_landmarks_residual(
    frame_bgr: np.ndarray,
    landmarks_5: np.ndarray,
    engine: "GfpganOnnxEngine",
    weight: float = 0.5,
    fp16: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """ONNX GFPGAN на 512-кропе по kps + diff-paste. fp16 не используется."""
    del fp16
    with _onnx_restore_lock:
        try:
            from insightface.utils import face_align

            from app.generators.inswapper import InswapperEngine

            ws = 512
            aimg_512, m512 = face_align.norm_crop2(frame_bgr, landmarks_5, ws)

            import torch

            crop = (
                torch.from_numpy(aimg_512)
                .to(engine._device)
                .permute(2, 0, 1)
                .unsqueeze(0)
                .float()
            )
            restored_t = engine.restore_blend_bgr(crop, blend=weight)
            if engine._device.type == "cuda":
                torch.cuda.synchronize(engine._device)
            bgr_fake_512 = (
                restored_t.clamp(0, 255).permute(1, 2, 0).byte().cpu().numpy()
            )
            restored = InswapperEngine._paste_back_insightface(
                frame_bgr, bgr_fake_512, aimg_512, m512
            )
            residual = restored.astype(np.float32) - frame_bgr.astype(np.float32)
            return restored, residual
        except Exception as exc:
            logger.warning("onnx restore frame fail: %s", exc)
            return frame_bgr, np.zeros_like(frame_bgr, dtype=np.float32)
