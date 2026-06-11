"""Простой приёмник multipart для теста OUTPUT_UPLOAD_URL.

Запуск:
    .venv\\Scripts\\python.exe scripts\\mock_output_server.py --port 9090

В .env:
    OUTPUT_UPLOAD_ENABLED=true
    OUTPUT_UPLOAD_URL=http://127.0.0.1:9090/api/receive
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
import uvicorn

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "data" / "upload_inbox"

app = FastAPI(title="GIGAvibe mock output server")


@app.post("/api/receive")
async def receive(
    file: UploadFile = File(...),
    job_id: str = Form(""),
    filename: str = Form(""),
    download_url: str = Form(""),
    guest_label: str = Form(""),
    face_count: str = Form(""),
) -> dict:
    INBOX.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_name = filename or file.filename or "upload.jpg"
    dest = INBOX / f"{stamp}_{job_id or 'nojob'}_{safe_name}"
    data = await file.read()
    dest.write_bytes(data)
    print(
        f"[mock] job={job_id} guest={guest_label!r} faces={face_count} "
        f"bytes={len(data)} -> {dest.name}",
        flush=True,
    )
    return {
        "ok": True,
        "saved_as": dest.name,
        "job_id": job_id,
        "download_url": download_url,
    }


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "inbox": str(INBOX)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9090)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
