"""GFPGANv1.4 через ONNX + io-binding (Rope / VisoMaster)."""

from __future__ import annotations

import logging
import urllib.request
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_ONNX_PATH = ROOT / "models" / "gfpgan" / "GFPGANv1.4.onnx"
GFPGAN_ONNX_URL = (
    "https://github.com/visomaster/visomaster-assets/releases/download/v0.1.0/GFPGANv1.4.onnx"
)


def is_available(onnx_path: Path | None = None) -> bool:
    p = Path(onnx_path) if onnx_path else DEFAULT_ONNX_PATH
    return p.exists() and p.stat().st_size > 1_000_000


def ensure_onnx_model(path: Path | None = None) -> Path:
    p = Path(path) if path else DEFAULT_ONNX_PATH
    if is_available(p):
        return p
    p.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading GFPGANv1.4.onnx from %s …", GFPGAN_ONNX_URL)
    urllib.request.urlretrieve(GFPGAN_ONNX_URL, p)
    if not is_available(p):
        raise RuntimeError(f"Не удалось скачать GFPGAN ONNX: {p}")
    return p


class GfpganOnnxEngine:
    """GFPGAN 512×512, вход/выход (1,3,512,512), нормализация как в Rope."""

    def __init__(
        self,
        model_path: Path | None = None,
        providers: list | None = None,
        device_id: int = 0,
    ) -> None:
        import onnxruntime as ort
        import torch

        self.model_path = ensure_onnx_model(Path(model_path) if model_path else DEFAULT_ONNX_PATH)
        self.device_id = int(device_id)
        if providers is None:
            providers = [
                ("CUDAExecutionProvider", {"device_id": self.device_id}),
                "CPUExecutionProvider",
            ]
        self._sess = ort.InferenceSession(str(self.model_path), providers=providers)
        self._in_name = self._sess.get_inputs()[0].name
        self._out_name = self._sess.get_outputs()[0].name

        torch.set_grad_enabled(False)
        self._torch = torch
        dev = torch.device(f"cuda:{self.device_id}" if torch.cuda.is_available() else "cpu")
        self._device = dev
        self._in_buf = torch.empty((1, 3, 512, 512), dtype=torch.float32, device=dev).contiguous()
        self._out_buf = torch.empty((1, 3, 512, 512), dtype=torch.float32, device=dev).contiguous()
        self._io = None
        logger.info("GfpganOnnxEngine ready on %s (%s)", dev, self.model_path.name)

    def _bind_io(self) -> None:
        if self._io is not None:
            return
        io = self._sess.io_binding()
        io.bind_input(
            name=self._in_name,
            device_type="cuda",
            device_id=self.device_id,
            element_type=np.float32,
            shape=(1, 3, 512, 512),
            buffer_ptr=self._in_buf.data_ptr(),
        )
        io.bind_output(
            name=self._out_name,
            device_type="cuda",
            device_id=self.device_id,
            element_type=np.float32,
            shape=(1, 3, 512, 512),
            buffer_ptr=self._out_buf.data_ptr(),
        )
        self._io = io

    def restore_blend_bgr(
        self,
        face_bgr: "torch.Tensor",
        blend: float = 0.5,
    ) -> "torch.Tensor":
        """face_bgr: (1,3,512,512) float BGR 0..255 на cuda device_id. Возврат BGR 0..255."""
        torch = self._torch
        if face_bgr.device != self._device:
            face_bgr = face_bgr.to(self._device)
        if face_bgr.dim() == 3:
            face_bgr = face_bgr.unsqueeze(0)

        # Rope: /255, normalize (0.5,0.5,0.5)
        t = face_bgr.float() / 255.0
        t = (t - 0.5) / 0.5
        self._in_buf.copy_(t)

        self._bind_io()
        if self._device.type == "cuda":
            torch.cuda.synchronize(self._device)
        self._sess.run_with_iobinding(self._io)

        out = self._out_buf.squeeze(0)
        out = torch.clamp(out, -1.0, 1.0)
        out = (out + 1.0) / 2.0 * 255.0

        if not torch.isfinite(out).all():
            logger.warning("GFPGAN ONNX non-finite output — skip restore")
            return face_bgr.squeeze(0) if face_bgr.dim() == 4 else face_bgr

        alpha = float(np.clip(blend, 0.0, 1.0))
        blended = out * alpha + face_bgr.squeeze(0).float() * (1.0 - alpha)
        return blended.clamp(0, 255)


def new_gfpgan_onnx_engine(
    model_path: Path | None = None,
    device_id: int | None = None,
) -> GfpganOnnxEngine:
    """Отдельный ONNX-движок на restore-GPU (для pipelined-воркеров)."""
    from app.config import settings

    dev = int(
        device_id
        if device_id is not None
        else settings.ref_video_restore_device_id
    )
    path = Path(model_path) if model_path else _abs_onnx_path(settings)
    providers = [
        ("CUDAExecutionProvider", {"device_id": dev}),
        "CPUExecutionProvider",
    ]
    return GfpganOnnxEngine(model_path=path, providers=providers, device_id=dev)


def _abs_onnx_path(settings) -> Path:
    p = Path(settings.ref_video_gfpgan_onnx_path)
    if not p.is_absolute():
        p = ROOT / p
    return p
