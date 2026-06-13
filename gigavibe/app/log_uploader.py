"""Фоновая отправка логов киоска на photo_receiver для удалённой диагностики."""

from __future__ import annotations

import json
import logging
import re
import socket
import threading
import time
from pathlib import Path

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
_SAFE_SOURCE_RE = re.compile(r"[^A-Za-z0-9_.-]+")
_worker_started = False
_worker_lock = threading.Lock()


def _base_url() -> str | None:
    url = (settings.log_upload_url or settings.output_upload_url or "").strip().rstrip("/")
    if not url:
        return None
    for suffix in ("/api/receive", "/api/kiosk-logs"):
        if url.endswith(suffix):
            return url[: -len(suffix)]
    return url


def _headers() -> dict[str, str]:
    key = (settings.log_upload_api_key or settings.output_upload_api_key or "").strip()
    if not key:
        return {}
    mode = (settings.log_upload_auth or settings.output_upload_auth or "bearer").strip().lower()
    if mode == "x-api-key":
        return {"X-API-Key": key}
    return {"Authorization": f"Bearer {key}"}


def _kiosk_id() -> str:
    raw = (settings.log_upload_kiosk_id or "").strip() or socket.gethostname() or "kiosk"
    safe = _SAFE_SOURCE_RE.sub("_", raw).strip("._-")
    return safe or "kiosk"


def _state_path() -> Path:
    path = settings.data_dir / "log_upload_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_state() -> dict[str, dict]:
    path = _state_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("log_upload: state read failed: %s", exc)
        return {}
    return data if isinstance(data, dict) else {}


def _save_state(state: dict[str, dict]) -> None:
    _state_path().write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _configured_paths() -> list[Path]:
    raw = settings.log_upload_paths or "data/srv_out.log;data/srv_err.log;server.log"
    paths: list[Path] = []
    for item in re.split(r"[;,]", raw):
        value = item.strip()
        if not value:
            continue
        path = Path(value)
        paths.append(path if path.is_absolute() else ROOT / path)
    return paths


def _source_name(path: Path) -> str:
    safe = _SAFE_SOURCE_RE.sub("_", path.name).strip("._-")
    return safe or "server.log"


def _read_next_chunk(path: Path, state: dict[str, dict]) -> tuple[bytes, int, int] | None:
    if not path.is_file():
        return None

    stat = path.stat()
    size = stat.st_size
    if size <= 0:
        return None

    key = str(path.resolve())
    saved = state.get(key) or {}
    offset = int(saved.get("offset") or 0)
    if not saved or offset > size:
        initial_tail = max(0, int(settings.log_upload_initial_tail_bytes))
        offset = max(0, size - initial_tail)

    if offset >= size:
        return None

    max_bytes = max(16 * 1024, int(settings.log_upload_max_bytes))
    end = min(size, offset + max_bytes)
    with path.open("rb") as fh:
        fh.seek(offset)
        data = fh.read(end - offset)
    if not data:
        return None
    return data, offset, size


def _upload_chunk(client: httpx.Client, url: str, path: Path, data: bytes, offset: int, total_size: int) -> None:
    files = {
        "log_file": (
            _source_name(path),
            data,
            "text/plain; charset=utf-8",
        )
    }
    form = {
        "kiosk_id": _kiosk_id(),
        "source": _source_name(path),
        "offset": str(offset),
        "total_size": str(total_size),
    }
    resp = client.post(url, data=form, files=files, headers=_headers())
    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP {resp.status_code}: {(resp.text or '')[:300]}")


def process_log_upload_once() -> int:
    base = _base_url()
    if not base:
        return 0

    url = f"{base}/api/kiosk-logs"
    state = _load_state()
    sent = 0
    timeout = httpx.Timeout(float(settings.log_upload_timeout_sec), connect=10.0, write=30.0)
    with httpx.Client(timeout=timeout, http2=False) as client:
        for path in _configured_paths():
            chunk = _read_next_chunk(path, state)
            if chunk is None:
                continue
            data, offset, total_size = chunk
            _upload_chunk(client, url, path, data, offset, total_size)
            state[str(path.resolve())] = {
                "offset": offset + len(data),
                "total_size": total_size,
                "source": _source_name(path),
                "uploaded_at": time.time(),
            }
            _save_state(state)
            sent += len(data)
    return sent


def _worker_loop() -> None:
    while True:
        try:
            sent = process_log_upload_once()
            if sent:
                logger.debug("log_upload: sent %s bytes", sent)
        except Exception as exc:
            logger.warning("log_upload worker: %s", exc)
        time.sleep(max(10.0, float(settings.log_upload_interval_sec)))


def start_log_upload_worker() -> None:
    global _worker_started

    if not settings.log_upload_enabled:
        logger.info("log_upload disabled")
        return
    base = _base_url()
    if not base:
        logger.warning("log_upload enabled, but LOG_UPLOAD_URL/OUTPUT_UPLOAD_URL is empty")
        return
    with _worker_lock:
        if _worker_started:
            return
        thread = threading.Thread(target=_worker_loop, name="log-upload", daemon=True)
        thread.start()
        _worker_started = True
        logger.info(
            "log_upload worker started: kiosk=%s url=%s paths=%s",
            _kiosk_id(),
            base,
            ";".join(str(path) for path in _configured_paths()),
        )
