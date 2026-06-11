"""
Фестивальный портрет: SDXL + InstantID, один финальный кадр (glossy 3D + living portrait).
Промпт адаптируется под guest_profile; на выходе PNG (dolly-out на киоске через CSS).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from app.generators.base import VideoGenerator

logger = logging.getLogger(__name__)

PORTRAIT_MODES = frozenset({"festival_portrait", "portrait", "portrait_still"})


class FestivalPortraitGenerator(VideoGenerator):
    last_generation_sec: float | None = None
    last_stage_timings: dict[str, float] | None = None

    @classmethod
    def is_available(cls) -> bool:
        from app.generators.keyframe_instantid import KeyframeInstantIDGenerator

        return KeyframeInstantIDGenerator.is_available()

    @staticmethod
    def install_hint() -> str:
        return (
            "Festival portrait: SDXL + InstantID. "
            "Скачайте models/sdxl-base, models/InstantID, antelopev2, vendor/instantid. "
            "См. scripts/test_festival_portrait.py"
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
        from app.generators.keyframe_instantid import KeyframeInstantIDGenerator
        from app.prompts import build_festival_portrait_prompt

        del fps, duration_sec  # анимация dolly-out — на фронте (CSS)

        t0 = time.perf_counter()
        prompt, negative = build_festival_portrait_prompt(guest_profile)
        if settings.instantid_prompt:
            prompt = settings.instantid_prompt
        if settings.instantid_negative_prompt:
            negative = settings.instantid_negative_prompt

        logger.info("festival_portrait prompt: %s", prompt[:240])

        t_gen = time.perf_counter()
        gen = KeyframeInstantIDGenerator()
        still = gen.generate_keyframe(
            source_image,
            width,
            height,
            prompt_override=prompt,
            negative_override=negative,
        )
        gen_sec = time.perf_counter() - t_gen

        out = output_path if output_path.suffix.lower() == ".png" else output_path.with_suffix(".png")
        out.parent.mkdir(parents=True, exist_ok=True)
        still.save(out, format="PNG")

        total = time.perf_counter() - t0
        type(self).last_generation_sec = gen_sec
        type(self).last_stage_timings = {
            "instantid_s": round(gen_sec, 3),
            "total_s": round(total, 3),
        }
        logger.info("festival_portrait done: instantid %.1fs, saved %s", gen_sec, out.name)
        return out
