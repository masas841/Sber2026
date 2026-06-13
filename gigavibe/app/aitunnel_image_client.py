"""Festival portrait через AITunnel (OpenAI Images API, без VPN)."""

from __future__ import annotations

import base64
import io
import json
import logging
import time
from pathlib import Path

import httpx
from PIL import Image

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.aitunnel.ru/v1"
DEFAULT_USER_AGENT = "GIGAvibe/1.0"

_MODEL_ALIASES = {
    "gemini-3.1-flash-image": "gemini-3.1-flash-image-preview",
    "gemini-3-pro-image": "gemini-3-pro-image-preview",
    "gemini-2.5-flash-image": "gemini-2.5-flash-image",
}


def _resolve_model(model: str) -> str:
    m = (model or "").strip()
    return _MODEL_ALIASES.get(m, m) or "gemini-3.1-flash-image-preview"


def _job_label(path: Path) -> str:
    return path.parent.name or path.stem


def _prepare_selfie_jpeg(path: Path, *, max_side: int = 1280) -> bytes:
    im = Image.open(path).convert("RGB")
    im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=88, optimize=True)
    return buf.getvalue()


def _decode_image_item(item: dict) -> Image.Image:
    if item.get("b64_json"):
        raw = base64.b64decode(item["b64_json"])
        return Image.open(io.BytesIO(raw)).convert("RGB")

    url = (item.get("url") or "").strip()
    if url.startswith("data:") and "base64," in url:
        b64 = url.split("base64,", 1)[1]
        return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")

    if url.startswith("http"):
        with httpx.Client(timeout=120.0, http2=False) as client:
            resp = client.get(url, headers={"User-Agent": DEFAULT_USER_AGENT})
            resp.raise_for_status()
            return Image.open(io.BytesIO(resp.content)).convert("RGB")

    raise RuntimeError(f"AITunnel: неизвестный формат ответа: {item!r}")


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
    resolved = _resolve_model(model)
    jpeg = _prepare_selfie_jpeg(source_image)
    logger.info(
        "aitunnel model=%s aspect=%s size=%s selfie=%s bytes prompt=%s…",
        resolved,
        aspect_ratio,
        image_size,
        source_image.name,
        len(jpeg),
        prompt[:160],
    )

    url = f"{base_url.rstrip('/')}/images/edits"
    image_config = json.dumps(
        {"aspect_ratio": aspect_ratio, "image_size": image_size},
        ensure_ascii=False,
    )
    headers = {"Authorization": f"Bearer {api_key.strip()}", "User-Agent": DEFAULT_USER_AGENT}
    files = {"image": ("selfie.jpg", jpeg, "image/jpeg")}
    data = {
        "model": resolved,
        "prompt": prompt,
        "image_config": image_config,
        "output_format": "jpeg",
        "output_compression": "92",
    }

    timeout = httpx.Timeout(300.0, connect=30.0, read=300.0, write=120.0)
    last_exc: BaseException | None = None
    job_label = _job_label(source_image)
    for attempt in range(1, 4):
        t_attempt = time.perf_counter()
        try:
            logger.info("aitunnel job=%s attempt=%s POST %s", job_label, attempt, url)
            with httpx.Client(timeout=timeout, http2=False) as client:
                resp = client.post(url, headers=headers, files=files, data=data)
            elapsed = time.perf_counter() - t_attempt
            logger.info(
                "aitunnel job=%s attempt=%s response status=%s time=%.1fs bytes=%s content-type=%s",
                job_label,
                attempt,
                resp.status_code,
                elapsed,
                len(resp.content),
                resp.headers.get("content-type", ""),
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"AITunnel API HTTP {resp.status_code}: {resp.text[:800]}")
            payload = resp.json()
            break
        except RuntimeError:
            raise
        except httpx.HTTPError as exc:
            last_exc = exc
            elapsed = time.perf_counter() - t_attempt
            logger.warning(
                "aitunnel job=%s attempt=%s HTTP error after %.1fs: %s",
                job_label,
                attempt,
                elapsed,
                repr(exc),
            )
            if attempt < 3:
                time.sleep(attempt * 2)
                continue
            raise RuntimeError(f"AITunnel API: {exc}") from exc
    else:
        if last_exc is not None:
            raise RuntimeError(f"AITunnel API: {last_exc}") from last_exc
        raise RuntimeError("AITunnel API: не удалось выполнить запрос")

    items = payload.get("data") or []
    if not items:
        raise RuntimeError(f"AITunnel: пустой data: {payload}")
    first_item = items[0]
    first_keys = sorted(first_item.keys()) if isinstance(first_item, dict) else type(first_item).__name__
    logger.info("aitunnel job=%s data items=%s first_keys=%s", job_label, len(items), first_keys)
    try:
        image = _decode_image_item(first_item)
    except Exception:
        logger.exception("aitunnel job=%s image decode failed", job_label)
        raise
    logger.info("aitunnel job=%s decoded image %sx%s", job_label, image.width, image.height)
    return image


def generate_scene_image(
    *,
    api_key: str,
    base_url: str,
    model: str,
    prompt: str,
    aspect_ratio: str,
    image_size: str,
) -> Image.Image:
    """Text-to-image (без референса) через AITunnel /images/generations."""
    resolved = _resolve_model(model)
    logger.info(
        "aitunnel generate model=%s aspect=%s size=%s prompt=%s…",
        resolved,
        aspect_ratio,
        image_size,
        prompt[:160],
    )

    url = f"{base_url.rstrip('/')}/images/generations"
    headers = {"Authorization": f"Bearer {api_key.strip()}", "User-Agent": DEFAULT_USER_AGENT}
    body = {
        "model": resolved,
        "prompt": prompt,
        "image_config": {"aspect_ratio": aspect_ratio, "image_size": image_size},
        "output_format": "jpeg",
        "output_compression": "92",
    }

    timeout = httpx.Timeout(300.0, connect=30.0, read=300.0, write=120.0)
    last_exc: BaseException | None = None
    for attempt in range(1, 4):
        try:
            with httpx.Client(timeout=timeout, http2=False) as client:
                resp = client.post(url, headers=headers, json=body)
            if resp.status_code >= 400:
                raise RuntimeError(f"AITunnel API HTTP {resp.status_code}: {resp.text[:800]}")
            payload = resp.json()
            break
        except RuntimeError:
            raise
        except httpx.HTTPError as exc:
            last_exc = exc
            if attempt < 3:
                time.sleep(attempt * 2)
                continue
            raise RuntimeError(f"AITunnel API: {exc}") from exc
    else:
        if last_exc is not None:
            raise RuntimeError(f"AITunnel API: {last_exc}") from last_exc
        raise RuntimeError("AITunnel API: не удалось выполнить запрос")

    items = payload.get("data") or []
    if not items:
        raise RuntimeError(f"AITunnel: пустой data: {payload}")
    return _decode_image_item(items[0])
