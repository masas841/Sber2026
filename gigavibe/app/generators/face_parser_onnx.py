"""BiSeNet face parser (ResNet34) через ONNX + io-binding (VisoMaster assets).

Сегментация лица на 19 классов. Используется для масок глаз/рта/зубов —
в этих зонах возвращаем оригинальные пиксели референса поверх свопа (приём
VisoMaster Face Parser Mask), убирая «галлюцинации» GFPGAN на глазах и зубах.
"""

from __future__ import annotations

import logging
import urllib.request
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PARSER_PATH = ROOT / "models" / "faceparser" / "faceparser_resnet34.onnx"
PARSER_URL = (
    "https://github.com/visomaster/visomaster-assets/releases/download/v0.1.0/"
    "faceparser_resnet34.onnx"
)

# Классы BiSeNet (zllrunning/yakhyo face-parsing):
#  0 bg 1 skin 2 l_brow 3 r_brow 4 l_eye 5 r_eye 6 eye_g 7 l_ear 8 r_ear
#  9 ear_r 10 nose 11 mouth 12 u_lip 13 l_lip 14 neck 15 neck_l 16 cloth 17 hair 18 hat
EYE_CLASSES = (4, 5)
BROW_CLASSES = (2, 3)  # l_brow, r_brow
MOUTH_CLASSES = (11, 12, 13)  # рот (зубы) + губы


def is_available(parser_path: Path | None = None) -> bool:
    p = Path(parser_path) if parser_path else DEFAULT_PARSER_PATH
    return p.exists() and p.stat().st_size > 1_000_000


def ensure_parser_model(path: Path | None = None) -> Path:
    p = Path(path) if path else DEFAULT_PARSER_PATH
    if is_available(p):
        return p
    p.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading faceparser_resnet34.onnx from %s …", PARSER_URL)
    urllib.request.urlretrieve(PARSER_URL, p)
    if not is_available(p):
        raise RuntimeError(f"Не удалось скачать face parser: {p}")
    return p


class FaceParserEngine:
    """BiSeNet 512×512, вход (1,3,512,512) RGB ImageNet-norm, выход (1,19,512,512)."""

    def __init__(
        self,
        model_path: Path | None = None,
        providers: list | None = None,
        device_id: int = 0,
    ) -> None:
        import onnxruntime as ort
        import torch

        self.model_path = ensure_parser_model(
            Path(model_path) if model_path else DEFAULT_PARSER_PATH
        )
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
        dev = torch.device(
            f"cuda:{self.device_id}" if torch.cuda.is_available() else "cpu"
        )
        self._device = dev
        # ImageNet нормализация (BiSeNet face-parsing).
        self._mean = torch.tensor([0.485, 0.456, 0.406], device=dev).view(1, 3, 1, 1)
        self._std = torch.tensor([0.229, 0.224, 0.225], device=dev).view(1, 3, 1, 1)
        self._in_buf = torch.empty(
            (1, 3, 512, 512), dtype=torch.float32, device=dev
        ).contiguous()
        self._io = None
        logger.info("FaceParserEngine ready on %s (%s)", dev, self.model_path.name)

    def _bind_input(self) -> None:
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
        # Выход оставляем на устройстве (форму берём из ORT — динамична по классам).
        io.bind_output(self._out_name, device_type="cuda", device_id=self.device_id)
        self._io = io

    def region_mask(
        self,
        face_bgr_512: "torch.Tensor",
        classes: tuple[int, ...],
        feather: int = 6,
        exclude: tuple[int, ...] = (),
    ) -> "torch.Tensor":
        """face_bgr_512: (1,3,512,512) BGR 0..255 на cuda. Возврат маски (1,1,512,512) 0..1.

        exclude: классы, жёстко вычитаемые из финальной маски (после feather) —
        напр. брови, чтобы feather глаз не растекался на бровь и не дублировал её.
        """
        torch = self._torch
        import torch.nn.functional as F

        if face_bgr_512.device != self._device:
            face_bgr_512 = face_bgr_512.to(self._device)
        if face_bgr_512.dim() == 3:
            face_bgr_512 = face_bgr_512.unsqueeze(0)

        rgb = face_bgr_512[:, [2, 1, 0], :, :] / 255.0
        rgb = (rgb - self._mean) / self._std
        self._in_buf.copy_(rgb)

        self._bind_input()
        if self._device.type == "cuda":
            torch.cuda.synchronize(self._device)
        self._sess.run_with_iobinding(self._io)
        out = self._io.get_outputs()[0]
        logits = torch.from_numpy(out.numpy()).to(self._device)
        if logits.dim() == 3:
            logits = logits.unsqueeze(0)

        parsing = logits.argmax(dim=1)  # (1,512,512)
        mask = torch.zeros_like(parsing, dtype=torch.float32)
        for c in classes:
            mask = mask + (parsing == c).float()
        mask = mask.clamp(0, 1).unsqueeze(1)  # (1,1,512,512)

        if feather and feather > 0:
            k = int(feather)
            mask = F.max_pool2d(mask, kernel_size=3, stride=1, padding=1)
            mask = F.avg_pool2d(mask, kernel_size=2 * k + 1, stride=1, padding=k)

        if exclude:
            ex = torch.zeros_like(parsing, dtype=torch.float32)
            for c in exclude:
                ex = ex + (parsing == c).float()
            # лёгкое расширение зоны исключения, чтобы перекрыть feather-растекание
            ex = ex.clamp(0, 1).unsqueeze(1)
            ex = F.max_pool2d(ex, kernel_size=5, stride=1, padding=2)
            mask = mask * (1.0 - ex.clamp(0, 1))

        return mask.clamp(0, 1)


def new_face_parser_engine(
    model_path: Path | None = None,
    device_id: int | None = None,
) -> FaceParserEngine:
    from app.config import settings

    dev = int(device_id if device_id is not None else settings.ref_video_swap_device_id)
    p = Path(model_path) if model_path else _abs_parser_path(settings)
    providers = [
        ("CUDAExecutionProvider", {"device_id": dev}),
        "CPUExecutionProvider",
    ]
    return FaceParserEngine(model_path=p, providers=providers, device_id=dev)


def _abs_parser_path(settings) -> Path:
    p = Path(settings.ref_video_parser_path)
    if not p.is_absolute():
        p = ROOT / p
    return p
