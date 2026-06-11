"""Локальная очередь незавершённых upload (докачка при обрыве связи)."""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

_worker_started = False
_worker_lock = threading.Lock()


@dataclass
class PendingUpload:
    job_id: str
    output_path: str
    output_filename: str
    download_url: str
    upload_id: str | None = None
    received_bytes: int = 0
    attempts: int = 0
    last_error: str | None = None


def _queue_dir() -> Path:
    d = settings.data_dir / "upload_queue"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _entry_path(job_id: str) -> Path:
    return _queue_dir() / f"{job_id}.json"


def enqueue_pending(entry: PendingUpload) -> None:
    _entry_path(entry.job_id).write_text(
        json.dumps(asdict(entry), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def dequeue_pending(job_id: str) -> None:
    path = _entry_path(job_id)
    if path.exists():
        path.unlink(missing_ok=True)


def list_pending() -> list[PendingUpload]:
    items: list[PendingUpload] = []
    for path in sorted(_queue_dir().glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            items.append(PendingUpload(**data))
        except Exception as exc:
            logger.warning("upload_queue: skip %s: %s", path.name, exc)
    return items


def process_pending_once() -> int:
    from app.output_dispatch import should_upload_file
    from app.upload_client import upload_output_with_resume

    if not should_upload_file():
        return 0

    done = 0
    for entry in list_pending():
        path = Path(entry.output_path)
        if not path.exists():
            dequeue_pending(entry.job_id)
            continue
        try:
            public_url, upload_id, received = upload_output_with_resume(
                path,
                entry.job_id,
                download_url=entry.download_url,
                output_filename=entry.output_filename,
                upload_id=entry.upload_id,
                start_offset=entry.received_bytes,
            )
            dequeue_pending(entry.job_id)
            done += 1
            logger.info(
                "upload_queue: completed job=%s url=%s bytes=%s",
                entry.job_id,
                public_url,
                received,
            )
        except Exception as exc:
            entry.attempts += 1
            entry.last_error = str(exc)
            enqueue_pending(entry)
            logger.warning("upload_queue: retry job=%s: %s", entry.job_id, exc)
    return done


def _worker_loop() -> None:
    while True:
        try:
            process_pending_once()
        except Exception as exc:
            logger.warning("upload_queue worker: %s", exc)
        time.sleep(max(5.0, float(settings.output_upload_retry_delay_sec)))


def start_upload_queue_worker() -> None:
    global _worker_started
    from app.output_dispatch import should_upload_file

    if not should_upload_file():
        return
    with _worker_lock:
        if _worker_started:
            return
        t = threading.Thread(target=_worker_loop, name="upload-queue", daemon=True)
        t.start()
        _worker_started = True
        logger.info("upload_queue worker started")
