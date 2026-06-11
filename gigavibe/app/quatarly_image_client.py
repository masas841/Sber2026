"""Gemini image generation через Quatarly (OpenAI-compatible chat/completions)."""

from __future__ import annotations

import base64
import io
import logging
import time
from pathlib import Path

import httpx
from PIL import Image

from app.selfie_compress import MAX_SELFIE_UPLOAD_BYTES, MAX_SELFIE_UPLOAD_SIDE, compress_selfie_jpeg

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.quatarly.cloud/v1"
DEFAULT_USER_AGENT = "GIGAvibe/1.0"
MAX_UPLOAD_BYTES = MAX_SELFIE_UPLOAD_BYTES
MAX_UPLOAD_SIDE = MAX_SELFIE_UPLOAD_SIDE


def _raise_api_error(exc: BaseException, *, context: str = "Quatarly API") -> None:
    msg = str(exc)
    lower = msg.lower()
    hint = ""
    if "unexpected_eof" in lower or "eof occurred" in lower or "ssl" in lower:
        hint = (
            " Обрыв SSL — часто VPN/Clash режет большие POST. "
            "DIRECT для api.quatarly.cloud + больше timeout."
        )
    elif "disconnected" in lower or "remoteprotocol" in lower:
        hint = (
            " Обрыв ~20 с — типичный таймаут VPN на длинный запрос генерации. "
            "Отключите TUN/прокси для Python или увеличьте timeout в Clash."
        )
    raise RuntimeError(f"{context}: {msg}.{hint}") from exc


def _encode_source_image(path: Path) -> str:
    """JPEG data URL — под лимит upload VPN (~20 КБ)."""
    raw = compress_selfie_jpeg(path, max_bytes=MAX_UPLOAD_BYTES, max_side=MAX_UPLOAD_SIDE)
    im = Image.open(io.BytesIO(raw))
    logger.info(
        "quatarly upload encode: %dx%d jpeg bytes=%s",
        im.width,
        im.height,
        len(raw),
    )
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def _post_json(url: str, *, api_key: str, body: dict, timeout_sec: float = 300.0) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
        "User-Agent": DEFAULT_USER_AGENT,
    }
    timeout = httpx.Timeout(timeout_sec, connect=30.0, read=timeout_sec, write=120.0)
    last_exc: BaseException | None = None
    for attempt in range(1, 4):
        try:
            with httpx.Client(timeout=timeout, http2=False) as client:
                resp = client.post(url, json=body, headers=headers)
            if resp.status_code >= 400:
                raise RuntimeError(f"Quatarly API HTTP {resp.status_code}: {resp.text[:800]}")
            return resp.json()
        except RuntimeError:
            raise
        except httpx.HTTPError as exc:
            last_exc = exc
            if attempt < 3:
                delay = attempt * 2
                logger.warning("quatarly POST attempt %s failed: %s; retry in %ss", attempt, exc, delay)
                time.sleep(delay)
                continue
            _raise_api_error(exc)
    if last_exc is not None:
        _raise_api_error(last_exc)
    raise RuntimeError("Quatarly API: не удалось выполнить запрос")


def _extract_image(message: dict) -> Image.Image:
    for item in message.get("images") or []:
        url = (item.get("image_url") or {}).get("url") or ""
        if url.startswith("data:") and "base64," in url:
            b64 = url.split("base64,", 1)[1]
            return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
        if url.startswith("http"):
            with httpx.Client(timeout=120.0, http2=False) as client:
                resp = client.get(url, headers={"User-Agent": DEFAULT_USER_AGENT})
                resp.raise_for_status()
                return Image.open(io.BytesIO(resp.content)).convert("RGB")

    content = message.get("content")
    if isinstance(content, list):
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "image_url":
                url = (part.get("image_url") or {}).get("url") or ""
                if "base64," in url:
                    b64 = url.split("base64,", 1)[1]
                    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")

    raise RuntimeError("Quatarly не вернул изображение в message.images")


def generate_festival_portrait(
    *,
    api_key: str,
    base_url: str,
    model: str,
    prompt: str,
    source_image: Path,
    aspect_ratio: str,
    image_size: str,
) -> Image.Image:
    url = f"{base_url.rstrip('/')}/chat/completions"
    body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": _encode_source_image(source_image)}},
                ],
            }
        ],
        "max_tokens": 8192,
        "aspect_ratio": aspect_ratio,
        "image_size": image_size,
    }
    logger.info("quatarly model=%s aspect=%s prompt=%s…", model, aspect_ratio, prompt[:160])
    payload = _post_json(url, api_key=api_key, body=body)

    if payload.get("error"):
        raise RuntimeError(f"Quatarly API error: {payload['error']}")

    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError(f"Quatarly: пустой choices: {payload}")

    message = choices[0].get("message") or {}
    return _extract_image(message)
