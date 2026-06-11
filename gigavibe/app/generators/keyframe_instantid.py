"""Генерация СТАРТОВОГО (ключевого) кадра для LTX через SDXL + InstantID.

LTX-Video — аниматор: он оживляет поданный кадр, но почти не перерисовывает сцену.
Чтобы получить фотореалистичного гостя на фестивале (с сохранением лица), сначала
строим ключевой кадр этой моделью, а затем отдаём его в LTX img2vid.

Модели (крупные, лежат на D: через .env):
  - SDXL base                (settings.instantid_base_dir / instantid_base_model)
  - InstantID ControlNet+IP  (settings.instantid_repo_dir: ControlNetModel/, ip-adapter.bin)
  - antelopev2 (insightface) (settings.instantid_antelope_root / models/antelopev2)
  - vendored pipeline        (settings.instantid_pipeline_dir)
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent.parent

_pipe = None
_face_app = None


def _abs(p: Path) -> Path:
    p = Path(p)
    return p if p.is_absolute() else (ROOT / p)


class KeyframeInstantIDGenerator:
    """Фото гостя → фотореалистичный фестивальный ключевой кадр (identity-preserving)."""

    @staticmethod
    def is_available() -> bool:
        try:
            import torch

            if not torch.cuda.is_available():
                return False
        except ImportError:
            return False

        from app.config import settings

        repo = _abs(settings.instantid_repo_dir)
        pipe_dir = _abs(settings.instantid_pipeline_dir)
        controlnet = repo / "ControlNetModel" / "config.json"
        adapter = repo / "ip-adapter.bin"
        pipeline_file = pipe_dir / "pipeline_stable_diffusion_xl_instantid.py"
        return controlnet.exists() and adapter.exists() and pipeline_file.exists()

    @staticmethod
    def _load():
        global _pipe, _face_app
        if _pipe is not None:
            return _pipe, _face_app

        import torch

        from app.config import settings

        pipe_dir = _abs(settings.instantid_pipeline_dir)
        if str(pipe_dir) not in sys.path:
            sys.path.insert(0, str(pipe_dir))

        from diffusers.models import ControlNetModel
        from insightface.app import FaceAnalysis
        from pipeline_stable_diffusion_xl_instantid import (  # type: ignore
            StableDiffusionXLInstantIDPipeline,
        )

        dtype = torch.float16
        dev_id = int(getattr(settings, "instantid_device_id", 0))
        device = f"cuda:{dev_id}"

        antelope_root = _abs(settings.instantid_antelope_root)
        face_app = FaceAnalysis(
            name="antelopev2",
            root=str(antelope_root),
            providers=[
                ("CUDAExecutionProvider", {"device_id": dev_id}),
                "CPUExecutionProvider",
            ],
        )
        face_app.prepare(ctx_id=dev_id, det_size=(640, 640))

        repo = _abs(settings.instantid_repo_dir)
        controlnet = ControlNetModel.from_pretrained(
            str(repo / "ControlNetModel"), torch_dtype=dtype
        )

        base_dir = _abs(settings.instantid_base_dir)
        base = str(base_dir) if (base_dir / "model_index.json").exists() else settings.instantid_base_model

        # Скачан только fp16-вариант весов SDXL → грузим именно его.
        pipe = StableDiffusionXLInstantIDPipeline.from_pretrained(
            base, controlnet=controlnet, torch_dtype=dtype, variant="fp16"
        )
        pipe.load_ip_adapter_instantid(str(repo / "ip-adapter.bin"))
        pipe.to(device)
        try:
            pipe.enable_vae_tiling()
        except Exception:
            pass

        _pipe = pipe
        _face_app = face_app
        return _pipe, _face_app

    def generate_keyframe(
        self,
        source_image: Path,
        width: int,
        height: int,
        *,
        prompt_override: str | None = None,
        negative_override: str | None = None,
    ) -> Image.Image:
        import cv2
        import torch

        from app.config import settings
        from app.prompts import KEYFRAME_FESTIVAL_PROMPT, KEYFRAME_NEGATIVE_PROMPT

        pipe, face_app = self._load()

        from pipeline_stable_diffusion_xl_instantid import draw_kps  # type: ignore

        img = Image.open(source_image).convert("RGB")
        bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        faces = face_app.get(bgr)
        if not faces:
            raise RuntimeError("InstantID: лицо на фото не найдено")
        face = sorted(
            faces,
            key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
        )[-1]
        face_emb = face["embedding"]
        kps_img = draw_kps(img, face["kps"])

        # SDXL любит размеры кратные 8 и близкие к 1024 по длинной стороне
        gen_w, gen_h = _sdxl_dims(width, height)
        kps_img = kps_img.resize((gen_w, gen_h), Image.Resampling.LANCZOS)

        prompt = settings.instantid_prompt or KEYFRAME_FESTIVAL_PROMPT
        negative = settings.instantid_negative_prompt or KEYFRAME_NEGATIVE_PROMPT
        if prompt_override is not None:
            prompt = prompt_override
        if negative_override is not None:
            negative = negative_override

        result = pipe(
            prompt=prompt,
            negative_prompt=negative,
            image_embeds=face_emb,
            image=kps_img,
            controlnet_conditioning_scale=float(settings.instantid_controlnet_scale),
            ip_adapter_scale=float(settings.instantid_ip_scale),
            num_inference_steps=int(settings.instantid_steps),
            guidance_scale=float(settings.instantid_guidance),
            width=gen_w,
            height=gen_h,
        )
        keyframe = result.images[0]

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        return keyframe.resize((width, height), Image.Resampling.LANCZOS)


def _sdxl_dims(width: int, height: int, target_long: int = 1024) -> tuple[int, int]:
    """Масштабируем к ~1024 по длинной стороне, выравниваем к кратному 8."""
    if width >= height:
        w = target_long
        h = int(round(target_long * height / width))
    else:
        h = target_long
        w = int(round(target_long * width / height))
    w = max(512, w - (w % 8))
    h = max(512, h - (h % 8))
    return w, h


def unload() -> None:
    """Выгрузить SDXL+InstantID из VRAM (освободить место под LTX)."""
    global _pipe, _face_app
    if _pipe is None:
        return
    try:
        import torch

        del _pipe
        _pipe = None
        _face_app = None
        import gc

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        _pipe = None
        _face_app = None


def warmup_model() -> None:
    if KeyframeInstantIDGenerator.is_available():
        KeyframeInstantIDGenerator._load()
