"""Клиент chunked-upload на photo_receiver с докачкой и повторами."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

from app.config import settings

if TYPE_CHECKING:
    from app.guest_profile import GuestProfile

logger = logging.getLogger(__name__)


def _upload_base_url() -> str:
    url = (settings.output_upload_url or "").strip().rstrip("/")
    if not url:
        raise RuntimeError("OUTPUT_UPLOAD_URL не задан")
    if url.endswith("/api/receive"):
        return url[: -len("/api/receive")]
    return url


def _upload_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    key = (settings.output_upload_api_key or "").strip()
    if not key:
        return headers
    mode = (settings.output_upload_auth or "bearer").strip().lower()
    if mode == "x-api-key":
        headers["X-API-Key"] = key
    else:
        headers["Authorization"] = f"Bearer {key}"
    return headers


def _chunked_enabled() -> bool:
    url = (settings.output_upload_url or "").strip()
    if url.endswith("/api/receive"):
        return False
    return True


def upload_output_simple(
    output_path: Path,
    job_id: str,
    *,
    guest_profile: "GuestProfile | None" = None,
    download_url: str | None = None,
    output_filename: str | None = None,
) -> str | None:
    url = (settings.output_upload_url or "").strip()
    if url.endswith("/api/receive"):
        post_url = url
    else:
        post_url = f"{url.rstrip('/')}/api/receive"

    meta: dict[str, str] = {"job_id": job_id}
    if output_filename:
        meta["filename"] = output_filename
    if download_url:
        meta["download_url"] = download_url
    if guest_profile is not None:
        meta["guest_label"] = guest_profile.label_ru()
        meta["face_count"] = str(guest_profile.face_count)

    timeout = httpx.Timeout(settings.output_upload_timeout_sec, connect=15.0)
    mime = "image/jpeg" if output_path.suffix.lower() in {".jpg", ".jpeg"} else "application/octet-stream"
    with output_path.open("rb") as fh:
        files = {"file": (output_path.name, fh, mime)}
        with httpx.Client(timeout=timeout, http2=False) as client:
            resp = client.post(post_url, files=files, data=meta, headers=_upload_headers())
    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP {resp.status_code}: {(resp.text or '')[:300]}")
    data = resp.json()
    return data.get("public_url") or data.get("download_url")


def upload_output_chunked(
    output_path: Path,
    job_id: str,
    *,
    guest_profile: "GuestProfile | None" = None,
    download_url: str | None = None,
    output_filename: str | None = None,
    upload_id: str | None = None,
    start_offset: int = 0,
) -> tuple[str | None, str, int]:
    base = _upload_base_url()
    headers = _upload_headers()
    timeout = httpx.Timeout(settings.output_upload_timeout_sec, connect=15.0, write=120.0)
    total_size = output_path.stat().st_size
    filename = output_filename or output_path.name
    chunk_size = max(32 * 1024, int(settings.output_upload_chunk_size))

    with httpx.Client(timeout=timeout, http2=False) as client:
        if not upload_id:
            init_body = {
                "job_id": job_id,
                "filename": filename,
                "total_size": total_size,
                "download_url": download_url or "",
            }
            if guest_profile is not None:
                init_body["guest_label"] = guest_profile.label_ru()
                init_body["face_count"] = str(guest_profile.face_count)
            resp = client.post(
                f"{base}/api/uploads/init",
                json=init_body,
                headers=headers,
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"init HTTP {resp.status_code}: {(resp.text or '')[:300]}")
            init = resp.json()
            upload_id = init["upload_id"]
            start_offset = int(init.get("received_bytes") or 0)
            if init.get("complete"):
                return init.get("public_url"), upload_id, total_size
            chunk_size = int(init.get("chunk_size") or chunk_size)

        offset = start_offset
        with output_path.open("rb") as fh:
            fh.seek(offset)
            while offset < total_size:
                chunk = fh.read(chunk_size)
                if not chunk:
                    break
                chunk_headers = {
                    **headers,
                    "X-Upload-Offset": str(offset),
                    "Content-Type": "application/octet-stream",
                }
                resp = client.patch(
                    f"{base}/api/uploads/{upload_id}",
                    content=chunk,
                    headers=chunk_headers,
                )
                if resp.status_code >= 400:
                    raise RuntimeError(
                        f"chunk @{offset} HTTP {resp.status_code}: {(resp.text or '')[:300]}"
                    )
                result = resp.json()
                offset = int(result["received_bytes"])
                if result.get("complete"):
                    return result.get("public_url"), upload_id, offset

        status = client.get(
            f"{base}/api/uploads/{upload_id}/status",
            headers=headers,
        )
        if status.status_code == 200:
            data = status.json()
            if data.get("complete"):
                return data.get("public_url"), upload_id, int(data["received_bytes"])
    raise RuntimeError(f"upload incomplete: {offset}/{total_size} bytes")


def upload_output_with_resume(
    output_path: Path,
    job_id: str,
    *,
    guest_profile: "GuestProfile | None" = None,
    download_url: str | None = None,
    output_filename: str | None = None,
    upload_id: str | None = None,
    start_offset: int = 0,
) -> tuple[str | None, str | None, int]:
    """Возвращает (public_url, upload_id, received_bytes)."""
    if not _chunked_enabled():
        url = upload_output_simple(
            output_path,
            job_id,
            guest_profile=guest_profile,
            download_url=download_url,
            output_filename=output_filename,
        )
        return url, None, output_path.stat().st_size

    max_retries = max(1, int(settings.output_upload_max_retries))
    delay = float(settings.output_upload_retry_delay_sec)
    last_exc: Exception | None = None
    current_upload_id = upload_id
    current_offset = start_offset

    for attempt in range(1, max_retries + 1):
        try:
            public_url, current_upload_id, current_offset = upload_output_chunked(
                output_path,
                job_id,
                guest_profile=guest_profile,
                download_url=download_url,
                output_filename=output_filename,
                upload_id=current_upload_id,
                start_offset=current_offset,
            )
            logger.info(
                "output_upload: job=%s upload_id=%s bytes=%s",
                job_id,
                current_upload_id,
                current_offset,
            )
            return public_url, current_upload_id, current_offset
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "output_upload attempt %s/%s job=%s offset=%s: %s",
                attempt,
                max_retries,
                job_id,
                current_offset,
                exc,
            )
            if attempt < max_retries:
                time.sleep(delay * attempt)
                # следующая попытка — resume с current_upload_id/offset
    raise RuntimeError(str(last_exc) if last_exc else "upload failed")
