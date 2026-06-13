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

from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.aitunnel.ru/v1"
DEFAULT_USER_AGENT = "GIGAvibe/1.0"

_MODEL_ALIASES = {
    "gemini-3.1-flash-image": "gemini-3.1-flash-image-preview",
    "gemini-3-pro-image": "gemini-3-pro-image-preview",
    "gemini-2.5-flash-image": "gemini-2.5-flash-image",
}

_RETRYABLE_HTTP = frozenset({408, 429, 500, 502, 503, 504})
_RETRYABLE_ERROR_CODES = frozenset(
    {
        "no_images_generated",
        "server_error",
        "rate_limit_exceeded",
        "temporarily_unavailable",
    }
)


def _resolve_model(model: str) -> str:
    m = (model or "").strip()
    return _MODEL_ALIASES.get(m, m) or "gemini-3.1-flash-image-preview"


def _job_label(path: Path) -> str:
    return path.parent.name or path.stem


def _aitunnel_error_code(body: str) -> str | None:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    err = payload.get("error")
    if isinstance(err, dict):
        code = str(err.get("code") or "").strip()
        return code or None
    return None


def _should_retry_aitunnel(status: int, body: str) -> bool:
    if status in _RETRYABLE_HTTP or status >= 500:
        return True
    code = _aitunnel_error_code(body)
    return code in _RETRYABLE_ERROR_CODES


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


def _request_aitunnel_payload(
    *,
    job_label: str,
    url: str,
    max_attempts: int,
    read_timeout: float,
    request_call,
) -> dict:
    timeout = httpx.Timeout(connect=30.0, read=read_timeout, write=120.0, pool=30.0)
    last_exc: BaseException | None = None

    for attempt in range(1, max_attempts + 1):
        t_attempt = time.perf_counter()
        try:
            logger.info(
                "aitunnel job=%s attempt=%s/%s POST %s read_timeout=%.0fs",
                job_label,
                attempt,
                max_attempts,
                url,
                read_timeout,
            )
            with httpx.Client(timeout=timeout, http2=False) as client:
                resp = request_call(client, url)
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
                exc = RuntimeError(f"AITunnel API HTTP {resp.status_code}: {resp.text[:800]}")
                if attempt < max_attempts and _should_retry_aitunnel(resp.status_code, resp.text):
                    last_exc = exc
                    logger.warning(
                        "aitunnel job=%s attempt=%s/%s retryable API error after %.1fs: %s",
                        job_label,
                        attempt,
                        max_attempts,
                        elapsed,
                        exc,
                    )
                    continue
                raise exc

            payload = resp.json()
            if not (payload.get("data") or []):
                exc = RuntimeError(f"AITunnel: пустой data: {payload}")
                if attempt < max_attempts:
                    last_exc = exc
                    logger.warning(
                        "aitunnel job=%s attempt=%s/%s empty data after %.1fs",
                        job_label,
                        attempt,
                        max_attempts,
                        elapsed,
                    )
                    continue
                raise exc
            return payload
        except httpx.HTTPError as exc:
            last_exc = exc
            elapsed = time.perf_counter() - t_attempt
            logger.warning(
                "aitunnel job=%s attempt=%s/%s HTTP error after %.1fs: %s",
                job_label,
                attempt,
                max_attempts,
                elapsed,
                repr(exc),
            )
            if attempt < max_attempts:
                continue
            raise RuntimeError(f"AITunnel API: {exc}") from exc

    if last_exc is not None:
        raise RuntimeError(f"AITunnel API: {last_exc}") from last_exc
    raise RuntimeError("AITunnel API: не удалось выполнить запрос")


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

    read_timeout = max(5.0, float(settings.aitunnel_read_timeout_sec))
    max_attempts = max(1, int(settings.aitunnel_max_attempts))
    job_label = _job_label(source_image)

    payload = _request_aitunnel_payload(
        job_label=job_label,
        url=url,
        max_attempts=max_attempts,
        read_timeout=read_timeout,
        request_call=lambda client, post_url: client.post(
            post_url, headers=headers, files=files, data=data
        ),
    )

    first_item = payload["data"][0]
    first_keys = sorted(first_item.keys()) if isinstance(first_item, dict) else type(first_item).__name__
    logger.info("aitunnel job=%s data items=%s first_keys=%s", job_label, len(payload["data"]), first_keys)
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

    read_timeout = max(5.0, float(settings.aitunnel_read_timeout_sec))
    max_attempts = max(1, int(settings.aitunnel_max_attempts))

    payload = _request_aitunnel_payload(
        job_label="scene",
        url=url,
        max_attempts=max_attempts,
        read_timeout=read_timeout,
        request_call=lambda client, post_url: client.post(post_url, headers=headers, json=body),
    )
    return _decode_image_item(payload["data"][0])
