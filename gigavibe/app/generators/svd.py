"""Локальный img2vid через Stable Video Diffusion (опционально)."""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from app.generators.base import VideoGenerator
from app.generators.cinematic import _apply_festival_grade


_shared_pipe = None
_shared_config: tuple | None = None


def warmup_model() -> None:
    """Предзагрузка модели при старте киоска."""
    if not SvdGenerator.is_available():
        return
    from app.config import settings

    gen = SvdGenerator(
        model_id=settings.svd_model_id,
        num_frames=settings.svd_num_frames,
        decode_chunk_size=settings.svd_decode_chunk_size,
        inference_steps=settings.svd_inference_steps,
    )
    gen._load_pipeline()


class SvdGenerator(VideoGenerator):
    def __init__(
        self,
        model_id: str,
        num_frames: int,
        decode_chunk_size: int,
        inference_steps: int,
    ) -> None:
        self.model_id = model_id
        self.num_frames = num_frames
        self.decode_chunk_size = decode_chunk_size
        self.inference_steps = inference_steps

    @staticmethod
    def is_available() -> bool:
        try:
            import torch

            return torch.cuda.is_available()
        except ImportError:
            return False

    def _load_pipeline(self):
        global _shared_pipe, _shared_config

        key = (
            self.model_id,
            self.num_frames,
            self.decode_chunk_size,
            self.inference_steps,
        )
        if _shared_pipe is not None and _shared_config == key:
            return _shared_pipe

        import torch
        from diffusers import StableVideoDiffusionPipeline

        pipe = StableVideoDiffusionPipeline.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16,
            variant="fp16",
        )
        pipe.enable_model_cpu_offload()
        try:
            pipe.enable_vae_slicing()
        except Exception:
            pass

        _shared_pipe = pipe
        _shared_config = key
        return _shared_pipe

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
        if not self.is_available():
            raise RuntimeError("CUDA/torch недоступны для SVD")

        import torch

        pipe = self._load_pipeline()
        self._pipe = pipe
        image = Image.open(source_image).convert("RGB")

        max_side = 768
        scale = max_side / max(image.size)
        if scale < 1:
            image = image.resize(
                (int(image.width * scale), int(image.height * scale)),
                Image.Resampling.LANCZOS,
            )

        result = pipe(
            image,
            num_frames=self.num_frames,
            decode_chunk_size=self.decode_chunk_size,
            num_inference_steps=self.inference_steps,
            generator=torch.manual_seed(42),
        )
        frames_rgb = result.frames[0]

        target_count = max(int(fps * duration_sec), 1)
        bgr_frames = self._frames_to_bgr_list(frames_rgb, width, height, target_count)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        for frame in bgr_frames:
            writer.write(_apply_festival_grade(frame))
        writer.release()

        from app.video_encode import ensure_browser_mp4

        ensure_browser_mp4(output_path, fps)
        return output_path

    @staticmethod
    def _frames_to_bgr_list(
        frames_rgb: list,
        width: int,
        height: int,
        target_count: int,
    ) -> list[np.ndarray]:
        resized: list[np.ndarray] = []
        for fr in frames_rgb:
            arr = np.array(fr)
            if arr.ndim == 2:
                arr = np.stack([arr] * 3, axis=-1)
            bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            bgr = SvdGenerator._center_crop_resize(bgr, width, height)
            resized.append(bgr)

        if not resized:
            raise RuntimeError("SVD не вернул кадры")

        out: list[np.ndarray] = []
        for i in range(target_count):
            idx = int(i / target_count * len(resized))
            idx = min(idx, len(resized) - 1)
            out.append(resized[idx])
        return out

    @staticmethod
    def _center_crop_resize(frame: np.ndarray, width: int, height: int) -> np.ndarray:
        h, w = frame.shape[:2]
        target_ratio = width / height
        src_ratio = w / h

        if src_ratio > target_ratio:
            new_w = int(h * target_ratio)
            x1 = (w - new_w) // 2
            crop = frame[:, x1 : x1 + new_w]
        else:
            new_h = int(w / target_ratio)
            y1 = (h - new_h) // 2
            crop = frame[y1 : y1 + new_h, :]

        return cv2.resize(crop, (width, height), interpolation=cv2.INTER_LANCZOS4)
