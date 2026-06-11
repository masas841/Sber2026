"""Кадрирование 9:16 и масштаб без размытия при апскейле."""

from __future__ import annotations

import cv2
import numpy as np


def _even(n: int) -> int:
    n = max(2, int(n))
    return n if n % 2 == 0 else n - 1


def crop_dimensions(
    frame_w: int, frame_h: int, target_w: int, target_h: int
) -> tuple[int, int]:
    target_ratio = target_w / target_h
    src_ratio = frame_w / frame_h
    if src_ratio > target_ratio:
        return _even(int(frame_h * target_ratio)), _even(frame_h)
    return _even(frame_w), _even(int(frame_w / target_ratio))


def effective_output_size(
    frame_w: int,
    frame_h: int,
    target_w: int,
    target_h: int,
    *,
    no_upscale: bool,
) -> tuple[int, int]:
    """Не растягивать кадр выше нативного разрешения референса (меньше «мыла»)."""
    cw, ch = crop_dimensions(frame_w, frame_h, target_w, target_h)
    if no_upscale and (cw < target_w or ch < target_h):
        return cw, ch
    return _even(target_w), _even(target_h)


def fit_frame_bgr(frame: np.ndarray, width: int, height: int) -> np.ndarray:
    h, w = frame.shape[:2]
    target_ratio = width / height
    src_ratio = w / h

    if src_ratio > target_ratio:
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        crop = frame[:, left : left + new_w]
    else:
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        crop = frame[top : top + new_h, :]

    ch, cw = crop.shape[:2]
    if cw == width and ch == height:
        return crop
    interp = (
        cv2.INTER_AREA
        if cw > width or ch > height
        else cv2.INTER_LANCZOS4
    )
    return cv2.resize(crop, (width, height), interpolation=interp)
