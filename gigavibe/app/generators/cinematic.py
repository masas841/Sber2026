"""Быстрый офлайн-генератор: Ken Burns + фестивальная цветокоррекция."""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

from app.generators.base import VideoGenerator


def _apply_festival_grade(frame_bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.18, 0, 255)
    hsv[:, :, 2] = np.clip(hsv[:, :, 2] * 1.06, 0, 255)
    graded = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    tint = np.zeros_like(graded, dtype=np.float32)
    tint[:, :, 0] = 12
    tint[:, :, 1] = 28
    out = np.clip(graded.astype(np.float32) + tint, 0, 255).astype(np.uint8)

    h, w = out.shape[:2]
    y, x = np.ogrid[:h, :w]
    cx, cy = w / 2, h / 2
    vignette = 1 - 0.35 * np.sqrt(((x - cx) / (w * 0.55)) ** 2 + ((y - cy) / (h * 0.55)) ** 2)
    vignette = np.clip(vignette, 0.55, 1.0)
    return (out * vignette[..., None]).astype(np.uint8)


class CinematicGenerator(VideoGenerator):
    def generate(
        self,
        source_image: Path,
        output_path: Path,
        *,
        width: int,
        height: int,
        fps: int,
        duration_sec: float,
    ) -> Path:
        base = self.load_and_fit(source_image, width, height)
        base = ImageEnhance.Contrast(base).enhance(1.08)
        base = ImageEnhance.Color(base).enhance(1.15)
        base = base.filter(ImageFilter.UnsharpMask(radius=1.2, percent=90, threshold=2))

        frame_count = max(int(fps * duration_sec), 1)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        src = np.array(base)[:, :, ::-1]
        pad = int(min(width, height) * 0.12)
        padded = cv2.copyMakeBorder(src, pad, pad, pad, pad, cv2.BORDER_REFLECT_101)

        for i in range(frame_count):
            t = i / max(frame_count - 1, 1)
            zoom = 1.0 + 0.14 * t
            pan_x = int((padded.shape[1] - width / zoom) * 0.35 * t)
            pan_y = int((padded.shape[0] - height / zoom) * 0.2 * (1 - t))

            crop_w = int(width / zoom)
            crop_h = int(height / zoom)
            x1 = min(max(pan_x, 0), padded.shape[1] - crop_w)
            y1 = min(max(pan_y, 0), padded.shape[0] - crop_h)

            crop = padded[y1 : y1 + crop_h, x1 : x1 + crop_w]
            frame = cv2.resize(crop, (width, height), interpolation=cv2.INTER_LANCZOS4)
            frame = _apply_festival_grade(frame)
            writer.write(frame)

        writer.release()

        from app.video_encode import ensure_browser_mp4

        ensure_browser_mp4(output_path, fps)
        return output_path
