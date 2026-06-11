"""Профили качества LTX: дольше генерация → больше кадров, шагов и «живости» сцены."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings


@dataclass(frozen=True)
class LtxQualityPreset:
    inference_steps: int
    max_frames: int
    guidance_scale: float
    decode_timestep: float
    decode_noise_scale: float
    cap_portrait: tuple[int, int]
    cap_landscape: tuple[int, int]
    hint: str


_PRESETS: dict[str, LtxQualityPreset] = {
    "fast": LtxQualityPreset(
        inference_steps=15,
        max_frames=25,
        guidance_scale=3.0,
        decode_timestep=0.08,
        decode_noise_scale=0.06,
        cap_portrait=(512, 704),
        cap_landscape=(768, 512),
        hint="~2–4 мин, лёгкое движение",
    ),
    "balanced": LtxQualityPreset(
        inference_steps=20,
        # Больше реальных кадров → меньше растяжки в _write_output_from_frames (меньше «фриза»).
        max_frames=65,
        guidance_scale=3.3,
        decode_timestep=0.12,
        decode_noise_scale=0.10,
        cap_portrait=(512, 704),
        cap_landscape=(768, 512),
        hint="~3–5 мин",
    ),
    "high": LtxQualityPreset(
        inference_steps=30,
        # 97 кадров (8k+1) — на 24 ГБ full-resident помещается; даёт почти 1:1 для 3 c @ 30 fps.
        max_frames=97,
        # Чуть ниже guidance — LTX i2v при высоком guidance «примораживает» сцену к keyframe.
        guidance_scale=3.5,
        decode_timestep=0.20,
        decode_noise_scale=0.15,
        # Портрет ближе к 9:16 (512x896) — на нём связность LTX заметно лучше, чем на 576x768.
        cap_portrait=(512, 896),
        cap_landscape=(768, 512),
        hint="~5–10 мин, сильнее движение и смена сцены",
    ),
}


def resolve_ltx_quality(settings: Settings) -> LtxQualityPreset:
    key = (settings.ltx_quality or "balanced").strip().lower()
    base = _PRESETS.get(key, _PRESETS["balanced"])
    return LtxQualityPreset(
        inference_steps=settings.ltx_inference_steps or base.inference_steps,
        max_frames=settings.ltx_num_frames or base.max_frames,
        guidance_scale=settings.ltx_guidance_scale or base.guidance_scale,
        decode_timestep=settings.ltx_decode_timestep
        if settings.ltx_decode_timestep is not None
        else base.decode_timestep,
        decode_noise_scale=settings.ltx_decode_noise_scale
        if settings.ltx_decode_noise_scale is not None
        else base.decode_noise_scale,
        cap_portrait=base.cap_portrait,
        cap_landscape=base.cap_landscape,
        hint=base.hint,
    )
