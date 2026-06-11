"""Прямая генерация изображений через Google Gemini API (Nano Banana)."""

from __future__ import annotations

import io
import logging
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


def _extract_image(response) -> Image.Image:
    for part in response.parts:
        if part.inline_data is not None:
            img = part.as_image()
            if img is not None:
                return img
        if part.inline_data and part.inline_data.data:
            return Image.open(io.BytesIO(part.inline_data.data)).convert("RGB")
    raise RuntimeError("Gemini API не вернул изображение (проверьте модель, ключ и квоту)")


def generate_festival_portrait(
    *,
    api_key: str,
    model: str,
    prompt: str,
    source_image: Path,
    aspect_ratio: str,
    image_size: str,
    base_url: str | None = None,
) -> Image.Image:
    from google import genai
    from google.genai import types

    ref = Image.open(source_image).convert("RGB")
    img_cfg = types.ImageConfig(aspect_ratio=aspect_ratio)
    if image_size and ("3.1" in model or "3-pro" in model or "pro-image" in model):
        img_cfg = types.ImageConfig(aspect_ratio=aspect_ratio, image_size=image_size)

    client_kwargs: dict = {"api_key": api_key.strip()}
    if base_url:
        client_kwargs["http_options"] = types.HttpOptions(base_url=base_url.rstrip("/"))

    client = genai.Client(**client_kwargs)
    logger.info("gemini model=%s aspect=%s prompt=%s…", model, aspect_ratio, prompt[:160])
    response = client.models.generate_content(
        model=model,
        contents=[prompt, ref],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=img_cfg,
        ),
    )
    return _extract_image(response)
