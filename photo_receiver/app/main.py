"""Приёмник портретов GIGAvibe: chunked upload, очередь, раздача /outputs/."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import settings
from app import storage

app = FastAPI(title="GIGAvibe Photo Receiver", version="1.0.0")

_STATIC = Path(__file__).resolve().parent.parent / "static"
_STUB_HTML = _STATIC / "index.html"
_PHOTO_HTML = _STATIC / "photo.html"

if _STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=_STATIC), name="static")


def _upload_path(filename: str) -> Path:
    safe = Path(filename).name
    if not safe or safe in {".", ".."}:
        raise HTTPException(404, "File not found")
    return settings.data_dir / "uploads" / safe


def _media_type(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(ext, "application/octet-stream")


class InitBody(BaseModel):
    job_id: str = Field(min_length=1, max_length=64)
    filename: str = Field(min_length=1, max_length=255)
    total_size: int = Field(gt=0)
    download_url: str = ""
    guest_label: str = ""
    face_count: str = ""


def _check_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = (settings.upload_api_key or "").strip()
    if not expected:
        return
    if (x_api_key or "").strip() != expected:
        raise HTTPException(401, "Invalid API key")


@app.on_event("startup")
def startup() -> None:
    storage.init_db()
    print(f"[photo-receiver] public={settings.public_base_url} port={settings.port}", flush=True)


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "public_base_url": settings.public_base_url,
        "chunk_size": settings.chunk_size,
    }


@app.post("/api/uploads/init")
def init_upload(body: InitBody, _: None = Depends(_check_api_key)) -> dict:
    meta = {
        "download_url": body.download_url,
        "guest_label": body.guest_label,
        "face_count": body.face_count,
    }
    try:
        return storage.resume_or_create(
            job_id=body.job_id,
            filename=Path(body.filename).name,
            total_size=body.total_size,
            meta=meta,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/uploads/{upload_id}/status")
def upload_status(upload_id: str, _: None = Depends(_check_api_key)) -> dict:
    try:
        return storage.upload_status(upload_id)
    except KeyError as exc:
        raise HTTPException(404, "Upload not found") from exc


@app.patch("/api/uploads/{upload_id}")
async def upload_chunk(
    upload_id: str,
    request: Request,
    x_upload_offset: int = Header(..., alias="X-Upload-Offset"),
    _: None = Depends(_check_api_key),
) -> dict:
    data = await request.body()
    if not data:
        raise HTTPException(400, "Empty chunk")
    try:
        return storage.append_chunk(upload_id, x_upload_offset, data)
    except KeyError as exc:
        raise HTTPException(404, "Upload not found") from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/api/receive")
async def receive_simple(
    file: UploadFile = File(...),
    job_id: str = Form(""),
    filename: str = Form(""),
    download_url: str = Form(""),
    guest_label: str = Form(""),
    face_count: str = Form(""),
    _: None = Depends(_check_api_key),
) -> dict:
    """Совместимость: простой multipart без докачки."""
    data = await file.read()
    safe_name = Path(filename or file.filename or "upload.jpg").name
    if not safe_name:
        safe_name = "upload.jpg"
    dest = settings.data_dir / "uploads" / safe_name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    public_url = storage.public_url_for(safe_name)
    print(
        f"[photo-receiver] simple job={job_id} bytes={len(data)} -> {dest.name}",
        flush=True,
    )
    return {
        "ok": True,
        "job_id": job_id,
        "saved_as": dest.name,
        "public_url": public_url,
        "download_url": public_url,
    }


@app.get("/p/{filename}", response_class=HTMLResponse)
def photo_page(filename: str) -> HTMLResponse:
    path = _upload_path(filename)
    if not path.exists():
        raise HTTPException(404, "File not found")
    safe = path.name
    image_url = f"/outputs/{safe}"
    download_url = f"/outputs/{safe}?download=1"
    if _PHOTO_HTML.is_file():
        html = _PHOTO_HTML.read_text(encoding="utf-8")
        html = html.replace("{{IMAGE_URL}}", image_url).replace("{{DOWNLOAD_URL}}", download_url)
        return HTMLResponse(html)
    return HTMLResponse(
        f'<!DOCTYPE html><html lang="ru"><body>'
        f'<img src="{image_url}" alt="фото" style="max-width:100%">'
        f'<p><a href="{download_url}">Скачать</a></p></body></html>'
    )


@app.get("/outputs/{filename}")
def download_output(filename: str, download: int = 0) -> FileResponse:
    path = _upload_path(filename)
    if not path.exists():
        raise HTTPException(404, "File not found")
    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{path.name}"'
    return FileResponse(
        path,
        media_type=_media_type(path),
        filename=path.name if download else None,
        headers=headers or None,
    )


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    if _STUB_HTML.is_file():
        return HTMLResponse(_STUB_HTML.read_text(encoding="utf-8"))
    return HTMLResponse(
        "<!DOCTYPE html><html lang='ru'><body><h1>СберФест 2026</h1></body></html>",
        status_code=200,
    )


def main() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
