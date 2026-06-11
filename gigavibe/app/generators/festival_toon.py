"""
Festival toon: PuLID-FLUX fp8 — Disney/Pixar 3D + brand-сцена, identity с селфи.

Локально на 8 GB: --fp8 + aggressive_offload (медленно, ~5–15 мин/кадр).
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image

from app.generators.base import VideoGenerator

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent.parent
_engine = None


def _abs(p: Path) -> Path:
    p = Path(p)
    return p if p.is_absolute() else (ROOT / p)


class _PulidFluxEngine:
    """Обёртка над vendor/pulid app_flux.FluxGenerator (singleton)."""

    def __init__(self) -> None:
        from app.config import settings

        pulid_root = _abs(settings.pulid_flux_dir)
        if str(pulid_root) not in sys.path:
            sys.path.insert(0, str(pulid_root))

        import torch

        args = SimpleNamespace(
            fp8=settings.pulid_flux_fp8,
            onnx_provider="cpu" if settings.pulid_flux_onnx_cpu else "gpu",
            version=settings.pulid_flux_version,
            pretrained_model=None,
        )

        from app_flux import FluxGenerator  # type: ignore  # noqa: E402

        self._gen = FluxGenerator(
            "flux-dev",
            "cuda",
            offload=settings.pulid_flux_offload,
            aggressive_offload=settings.pulid_flux_aggressive_offload,
            args=args,
        )
        self._settings = settings
        logger.info(
            "PuLID-FLUX ready fp8=%s offload=%s aggressive=%s",
            settings.pulid_flux_fp8,
            settings.pulid_flux_offload,
            settings.pulid_flux_aggressive_offload,
        )

    def generate(
        self,
        id_image: Image.Image,
        *,
        width: int,
        height: int,
        prompt: str,
        negative: str,
    ) -> Image.Image:
        s = self._settings
        rgb = np.array(id_image.convert("RGB"))
        img, seed, _ = self._gen.generate_image(
            width,
            height,
            s.pulid_flux_steps,
            s.pulid_flux_start_step,
            s.pulid_flux_guidance,
            -1,
            prompt,
            id_image=rgb,
            id_weight=s.pulid_flux_id_weight,
            neg_prompt=negative,
            true_cfg=s.pulid_flux_true_cfg,
            timestep_to_start_cfg=1,
            max_sequence_length=128,
        )
        logger.info("PuLID-FLUX seed=%s", seed)
        return img


def _get_engine() -> _PulidFluxEngine:
    global _engine
    if _engine is None:
        _engine = _PulidFluxEngine()
    return _engine


class FestivalToonGenerator(VideoGenerator):
    last_generation_sec: float | None = None
    last_stage_timings: dict[str, float] | None = None

    @classmethod
    def is_available(cls) -> bool:
        try:
            import torch

            if not torch.cuda.is_available():
                return False
        except ImportError:
            return False

        from app.config import settings

        models = _abs(Path("models"))
        ver = settings.pulid_flux_version
        pulid = models / f"pulid_flux_{ver}.safetensors"
        fp8 = models / "flux-dev-fp8.safetensors"
        ae = models / "ae.safetensors"
        pulid_code = _abs(settings.pulid_flux_dir) / "app_flux.py"
        return pulid.exists() and fp8.exists() and ae.exists() and pulid_code.exists()

    @staticmethod
    def install_hint() -> str:
        return (
            "Festival toon: PuLID-FLUX fp8. "
            "vendor/pulid + scripts/download_festival_toon_models.py + optimum-quanto. "
            "См. scripts/test_festival_toon.py"
        )

    def generate(
        self,
        source_image: Path,
        output_path: Path,
        *,
        width: int,
        height: int,
        fps: int,
        duration_sec: float,
        guest_profile=None,
    ) -> Path:
        from app.config import settings
        from app.prompts import build_festival_toon_prompt

        del fps, duration_sec, guest_profile

        prompt, negative = build_festival_toon_prompt(None)
        if settings.pulid_toon_prompt:
            prompt = settings.pulid_toon_prompt
        if settings.pulid_toon_negative:
            negative = settings.pulid_toon_negative

        logger.info("festival_toon prompt: %s", prompt[:200])

        t0 = time.perf_counter()
        id_img = Image.open(source_image).convert("RGB")
        still = _get_engine().generate(
            id_img,
            width=width,
            height=height,
            prompt=prompt,
            negative=negative,
        )
        gen_sec = time.perf_counter() - t0

        out = output_path if output_path.suffix.lower() == ".png" else output_path.with_suffix(".png")
        out.parent.mkdir(parents=True, exist_ok=True)
        still.save(out, format="PNG")

        type(self).last_generation_sec = gen_sec
        type(self).last_stage_timings = {"pulid_flux_s": round(gen_sec, 3)}
        logger.info("festival_toon done: %.1fs -> %s", gen_sec, out.name)
        return out
