"""SQLite-очередь загрузок и хранение файлов."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings

_lock = threading.Lock()


def _db_path() -> Path:
    return settings.data_dir / "queue.db"


@contextmanager
def _conn():
    con = sqlite3.connect(_db_path(), timeout=30)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    with _conn() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS uploads (
                upload_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                total_size INTEGER NOT NULL,
                received_bytes INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'receiving',
                meta_json TEXT NOT NULL DEFAULT '{}',
                part_path TEXT NOT NULL,
                final_path TEXT,
                public_url TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_uploads_job ON uploads(job_id);
            CREATE INDEX IF NOT EXISTS idx_uploads_status ON uploads(status);
            """
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def public_url_for(filename: str) -> str:
    """Публичная страница для QR (просмотр + скачивание)."""
    base = settings.public_base_url.rstrip("/")
    safe = Path(filename).name
    return f"{base}/p/{safe}"


def file_url_for(filename: str, *, download: bool = False) -> str:
    base = settings.public_base_url.rstrip("/")
    safe = Path(filename).name
    url = f"{base}/outputs/{safe}"
    if download:
        url += "?download=1"
    return url


def create_upload(
    *,
    job_id: str,
    filename: str,
    total_size: int,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if total_size <= 0 or total_size > settings.max_upload_bytes:
        raise ValueError(f"invalid total_size {total_size}")

    upload_id = uuid.uuid4().hex
    part_path = settings.data_dir / "parts" / f"{upload_id}.part"
    part_path.parent.mkdir(parents=True, exist_ok=True)
    part_path.write_bytes(b"")
    now = _now()
    meta_json = json.dumps(meta or {}, ensure_ascii=False)

    with _lock, _conn() as con:
        con.execute(
            """
            INSERT INTO uploads (
                upload_id, job_id, filename, total_size, received_bytes,
                status, meta_json, part_path, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 0, 'receiving', ?, ?, ?, ?)
            """,
            (upload_id, job_id, filename, total_size, meta_json, str(part_path), now, now),
        )
    return {
        "upload_id": upload_id,
        "chunk_size": settings.chunk_size,
        "received_bytes": 0,
        "total_size": total_size,
        "complete": False,
    }


def get_upload(upload_id: str) -> sqlite3.Row | None:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM uploads WHERE upload_id = ?", (upload_id,)
        ).fetchone()
    return row


def append_chunk(upload_id: str, offset: int, data: bytes) -> dict[str, Any]:
    with _lock:
        row = get_upload(upload_id)
        if row is None:
            raise KeyError("upload not found")
        if row["status"] != "receiving":
            raise RuntimeError(f"upload status={row['status']}")
        if offset != row["received_bytes"]:
            raise ValueError(
                f"offset mismatch: expected {row['received_bytes']}, got {offset}"
            )
        if offset + len(data) > row["total_size"]:
            raise ValueError("chunk exceeds total_size")

        part_path = Path(row["part_path"])
        with part_path.open("ab") as fh:
            fh.write(data)
        new_received = offset + len(data)
        complete = new_received >= row["total_size"]
        status = "complete" if complete else "receiving"
        now = _now()

        final_path = None
        public_url = None
        if complete:
            safe_name = Path(row["filename"]).name
            final_path = settings.data_dir / "uploads" / safe_name
            part_path.replace(final_path)
            public_url = public_url_for(safe_name)

        with _conn() as con:
            con.execute(
                """
                UPDATE uploads SET
                    received_bytes = ?, status = ?, updated_at = ?,
                    final_path = ?, public_url = ?,
                    completed_at = CASE WHEN ? THEN ? ELSE completed_at END
                WHERE upload_id = ?
                """,
                (
                    new_received,
                    status,
                    now,
                    str(final_path) if final_path else None,
                    public_url,
                    complete,
                    now if complete else None,
                    upload_id,
                ),
            )

    return {
        "upload_id": upload_id,
        "received_bytes": new_received,
        "total_size": row["total_size"],
        "complete": complete,
        "public_url": public_url,
    }


def upload_status(upload_id: str) -> dict[str, Any]:
    row = get_upload(upload_id)
    if row is None:
        raise KeyError("upload not found")
    return {
        "upload_id": upload_id,
        "job_id": row["job_id"],
        "filename": row["filename"],
        "received_bytes": row["received_bytes"],
        "total_size": row["total_size"],
        "status": row["status"],
        "complete": row["status"] == "complete",
        "public_url": row["public_url"],
        "chunk_size": settings.chunk_size,
    }


def find_by_job(job_id: str) -> sqlite3.Row | None:
    with _conn() as con:
        return con.execute(
            "SELECT * FROM uploads WHERE job_id = ? ORDER BY created_at DESC LIMIT 1",
            (job_id,),
        ).fetchone()


def resume_or_create(
    *,
    job_id: str,
    filename: str,
    total_size: int,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    existing = find_by_job(job_id)
    if existing and existing["status"] == "receiving":
        return {
            "upload_id": existing["upload_id"],
            "chunk_size": settings.chunk_size,
            "received_bytes": existing["received_bytes"],
            "total_size": existing["total_size"],
            "complete": False,
            "resumed": True,
        }
    if existing and existing["status"] == "complete":
        return {
            "upload_id": existing["upload_id"],
            "chunk_size": settings.chunk_size,
            "received_bytes": existing["total_size"],
            "total_size": existing["total_size"],
            "complete": True,
            "public_url": existing["public_url"],
            "resumed": True,
        }
    out = create_upload(job_id=job_id, filename=filename, total_size=total_size, meta=meta)
    out["resumed"] = False
    return out
