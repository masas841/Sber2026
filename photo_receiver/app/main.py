"""Приёмник портретов GIGAvibe: chunked upload, очередь, раздача /outputs/."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import settings
from app import storage

app = FastAPI(title="GIGAvibe Photo Receiver", version="1.0.0")

_STATIC = Path(__file__).resolve().parent.parent / "static"
_STUB_HTML = _STATIC / "index.html"
_PHOTO_HTML = _STATIC / "photo.html"
_SAFE_SEGMENT_RE = re.compile(r"[^A-Za-z0-9_.-]+")
_ERROR_LINE_RE = re.compile(
    r"\b(error|exception|traceback|failed|timeout|abort|critical|ошиб|исключ|сбой|таймаут)\b",
    re.IGNORECASE,
)
_LOGS_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>GIGAvibe realtime logs</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0b1116;
      --panel: #121b23;
      --panel-2: #182532;
      --text: #edf6ff;
      --muted: #8ea3b5;
      --ok: #32d583;
      --warn: #fdb022;
      --bad: #ff5f57;
      --border: rgba(255, 255, 255, 0.1);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: radial-gradient(circle at 20% 0%, #17324a 0, transparent 34rem), var(--bg);
      color: var(--text);
      font-family: Arial, sans-serif;
    }
    main {
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0 40px;
    }
    header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 20px;
      margin-bottom: 18px;
    }
    h1 {
      margin: 0 0 8px;
      font-size: 28px;
      letter-spacing: -0.02em;
    }
    .lead {
      margin: 0;
      color: var(--muted);
    }
    .status {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border: 1px solid var(--border);
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.06);
      white-space: nowrap;
    }
    .dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--warn);
      box-shadow: 0 0 16px currentColor;
    }
    .status[data-state="connected"] .dot { background: var(--ok); }
    .status[data-state="error"] .dot { background: var(--bad); }
    .grid {
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 16px;
    }
    .panel {
      border: 1px solid var(--border);
      border-radius: 18px;
      background: rgba(18, 27, 35, 0.92);
      overflow: hidden;
    }
    .panel h2 {
      margin: 0;
      padding: 14px 16px;
      border-bottom: 1px solid var(--border);
      font-size: 16px;
    }
    .sources,
    .feed {
      padding: 12px;
    }
    .source {
      display: block;
      padding: 10px 12px;
      margin-bottom: 8px;
      color: inherit;
      text-decoration: none;
      background: var(--panel-2);
      border-radius: 12px;
      border: 1px solid transparent;
    }
    .source:hover { border-color: rgba(255, 255, 255, 0.22); }
    .source small {
      display: block;
      color: var(--muted);
      margin-top: 4px;
      line-height: 1.35;
    }
    .toolbar {
      display: flex;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
      color: var(--muted);
    }
    label {
      display: inline-flex;
      gap: 8px;
      align-items: center;
      cursor: pointer;
      user-select: none;
    }
    button {
      color: var(--text);
      background: #203244;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 8px 10px;
      cursor: pointer;
    }
    button:hover { background: #294158; }
    .feed {
      max-height: calc(100vh - 190px);
      overflow: auto;
    }
    .log-card {
      margin: 0 0 10px;
      border: 1px solid var(--border);
      border-radius: 14px;
      background: #0f1720;
      overflow: hidden;
    }
    .only-errors .log-card:not(.has-error) { display: none; }
    .log-card.has-error { border-color: rgba(255, 95, 87, 0.65); }
    .meta {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      padding: 9px 12px;
      color: var(--muted);
      border-bottom: 1px solid var(--border);
      font-size: 13px;
    }
    .badge {
      padding: 3px 7px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.08);
      color: var(--text);
    }
    .has-error .badge-kind {
      background: rgba(255, 95, 87, 0.16);
      color: #ffb4af;
    }
    pre {
      margin: 0;
      padding: 12px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font: 12px/1.45 Consolas, Monaco, monospace;
      color: #d9e6f2;
    }
    .empty {
      padding: 24px;
      color: var(--muted);
      text-align: center;
    }
    @media (max-width: 860px) {
      header,
      .toolbar { align-items: stretch; flex-direction: column; }
      .grid { grid-template-columns: 1fr; }
      .feed { max-height: none; }
    }
  </style>
</head>
<body class="only-errors">
  <main>
    <header>
      <div>
        <h1>Realtime ошибки киосков</h1>
        <p class="lead">Новые чанки логов появляются здесь сразу после отправки с киоска.</p>
      </div>
      <div id="ws-status" class="status" data-state="connecting">
        <span class="dot"></span>
        <span id="ws-label">Подключение...</span>
      </div>
    </header>

    <section class="grid">
      <aside class="panel">
        <h2>Источники</h2>
        <div id="sources" class="sources">
          <div class="empty">Загружаем список...</div>
        </div>
      </aside>

      <section class="panel">
        <div class="toolbar">
          <label>
            <input id="only-errors" type="checkbox" checked />
            показывать только ошибки
          </label>
          <div>
            <span id="counter">0 событий</span>
            <button id="clear-feed" type="button">Очистить</button>
          </div>
        </div>
        <div id="feed" class="feed">
          <div class="empty">Ждём новые ошибки...</div>
        </div>
      </section>
    </section>
  </main>

  <script>
    const params = new URLSearchParams(location.search);
    const key = params.get("key") || "";
    const keySuffix = key ? `?key=${encodeURIComponent(key)}` : "";
    const statusBox = document.getElementById("ws-status");
    const statusLabel = document.getElementById("ws-label");
    const feed = document.getElementById("feed");
    const sources = document.getElementById("sources");
    const onlyErrors = document.getElementById("only-errors");
    const clearFeed = document.getElementById("clear-feed");
    const counter = document.getElementById("counter");
    let events = 0;
    let reconnectTimer = null;

    function setStatus(state, label) {
      statusBox.dataset.state = state;
      statusLabel.textContent = label;
    }

    function fmtBytes(value) {
      const n = Number(value) || 0;
      if (n > 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`;
      if (n > 1024) return `${(n / 1024).toFixed(1)} KB`;
      return `${n} B`;
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
    }

    async function loadSources() {
      try {
        const res = await fetch(`/api/kiosk-logs${keySuffix}`, { cache: "no-store" });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const items = data.items || [];
        if (!items.length) {
          sources.innerHTML = '<div class="empty">Пока нет логов</div>';
          return;
        }
        sources.innerHTML = items.map((item) => {
          const url = `${item.latest_url}${item.latest_url.includes("?") ? "&" : "?"}key=${encodeURIComponent(key)}`;
          return `<a class="source" href="${escapeHtml(url)}" target="_blank" rel="noopener">
            <strong>${escapeHtml(item.kiosk_id)} / ${escapeHtml(item.source)}</strong>
            <small>${fmtBytes(item.latest_bytes)} · chunks ${item.chunks} · ${escapeHtml(item.updated_at)}</small>
          </a>`;
        }).join("");
      } catch (err) {
        sources.innerHTML = `<div class="empty">Не удалось загрузить список: ${escapeHtml(err.message)}</div>`;
      }
    }

    function addEvent(data) {
      if (feed.querySelector(".empty")) feed.innerHTML = "";
      events += 1;
      counter.textContent = `${events} событий`;
      const card = document.createElement("article");
      card.className = `log-card${data.has_error ? " has-error" : ""}`;
      card.innerHTML = `
        <div class="meta">
          <span class="badge badge-kind">${data.has_error ? "ошибка" : "лог"}</span>
          <span class="badge">${escapeHtml(data.kiosk_id || "unknown")}</span>
          <span>${escapeHtml(data.source || "server.log")}</span>
          <span>${escapeHtml(data.received_at || "")}</span>
          <span>${fmtBytes(data.chunk_bytes)}</span>
          <span>offset ${data.offset ?? 0}</span>
        </div>
        <pre>${escapeHtml(data.text || "")}</pre>
      `;
      feed.prepend(card);
      while (feed.children.length > 200) {
        feed.lastElementChild?.remove();
      }
    }

    function connect() {
      window.clearTimeout(reconnectTimer);
      const proto = location.protocol === "https:" ? "wss:" : "ws:";
      const ws = new WebSocket(`${proto}//${location.host}/ws/kiosk-logs${keySuffix}`);
      setStatus("connecting", "Подключение...");

      ws.onopen = () => setStatus("connected", "Онлайн");
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "kiosk_log") {
          addEvent(data);
          loadSources();
        }
      };
      ws.onerror = () => setStatus("error", "Ошибка WebSocket");
      ws.onclose = () => {
        setStatus("error", "Отключено, переподключение...");
        reconnectTimer = window.setTimeout(connect, 2500);
      };
    }

    onlyErrors.addEventListener("change", () => {
      document.body.classList.toggle("only-errors", onlyErrors.checked);
    });
    clearFeed.addEventListener("click", () => {
      events = 0;
      counter.textContent = "0 событий";
      feed.innerHTML = '<div class="empty">Ждём новые ошибки...</div>';
    });

    loadSources();
    connect();
  </script>
</body>
</html>
"""

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


class LogWebSocketHub:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._clients.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._clients.discard(websocket)

    async def broadcast(self, payload: dict) -> None:
        stale: list[WebSocket] = []
        for websocket in list(self._clients):
            try:
                await websocket.send_json(payload)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(websocket)


log_ws_hub = LogWebSocketHub()


def _safe_segment(value: str, fallback: str) -> str:
    safe = _SAFE_SEGMENT_RE.sub("_", (value or "").strip()).strip("._-")
    return (safe or fallback)[:80]


def _kiosk_log_dir(kiosk_id: str, source: str) -> Path:
    return settings.data_dir / "kiosk_logs" / _safe_segment(kiosk_id, "unknown") / _safe_segment(source, "server.log")


def _is_api_token_valid(token: str | None) -> bool:
    expected = (settings.upload_api_key or "").strip()
    if not expected:
        return True
    return (token or "").strip() == expected


def _check_api_key(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    key: str = Query(default=""),
) -> None:
    if _is_api_token_valid(key):
        return
    bearer = ""
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer":
            bearer = token.strip()
    if not _is_api_token_valid(x_api_key) and not _is_api_token_valid(bearer):
        raise HTTPException(401, "Invalid API key")


def _decode_log_chunk(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace")
    if len(text) > 12000:
        return text[-12000:]
    return text


def _has_error_lines(text: str) -> bool:
    return bool(_ERROR_LINE_RE.search(text))


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
        "kiosk_logs": True,
        "kiosk_logs_realtime": True,
    }


@app.get("/logs", response_class=HTMLResponse)
def logs_page(key: str = Query(default="")) -> HTMLResponse:
    if not _is_api_token_valid(key):
        return HTMLResponse("Invalid API key", status_code=401)
    return HTMLResponse(_LOGS_HTML, headers={"Cache-Control": "no-cache, must-revalidate"})


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


@app.post("/api/kiosk-logs")
async def receive_kiosk_log(
    log_file: UploadFile = File(...),
    kiosk_id: str = Form(...),
    source: str = Form("server.log"),
    offset: int = Form(0),
    total_size: int = Form(0),
    _: None = Depends(_check_api_key),
) -> dict:
    data = await log_file.read()
    if not data:
        raise HTTPException(400, "Empty log chunk")
    if len(data) > settings.max_log_upload_bytes:
        raise HTTPException(413, "Log chunk is too large")

    safe_kiosk = _safe_segment(kiosk_id, "unknown")
    safe_source = _safe_segment(source, "server.log")
    log_dir = _kiosk_log_dir(safe_kiosk, safe_source)
    chunks_dir = log_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(UTC)
    chunk_name = f"{now:%Y%m%dT%H%M%SZ}_{max(0, offset):012d}.log"
    chunk_path = chunks_dir / chunk_name
    chunk_path.write_bytes(data)

    latest_path = log_dir / "latest.log"
    with latest_path.open("ab") as fh:
        fh.write(data)

    meta = {
        "kiosk_id": safe_kiosk,
        "source": safe_source,
        "received_at": now.isoformat(),
        "offset": max(0, offset),
        "chunk_bytes": len(data),
        "total_size": max(0, total_size),
        "latest_bytes": latest_path.stat().st_size,
        "chunk": chunk_name,
    }
    (log_dir / "latest.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"[photo-receiver] kiosk-log kiosk={safe_kiosk} source={safe_source} "
        f"offset={offset} bytes={len(data)}",
        flush=True,
    )
    text = _decode_log_chunk(data)
    await log_ws_hub.broadcast(
        {
            "type": "kiosk_log",
            "kiosk_id": safe_kiosk,
            "source": safe_source,
            "received_at": meta["received_at"],
            "offset": meta["offset"],
            "chunk_bytes": meta["chunk_bytes"],
            "total_size": meta["total_size"],
            "latest_bytes": meta["latest_bytes"],
            "has_error": _has_error_lines(text),
            "text": text,
        }
    )
    return {"ok": True, **meta}


@app.get("/api/kiosk-logs")
def list_kiosk_logs(_: None = Depends(_check_api_key)) -> dict:
    root = settings.data_dir / "kiosk_logs"
    items: list[dict] = []
    for kiosk_dir in sorted(root.glob("*")):
        if not kiosk_dir.is_dir():
            continue
        for source_dir in sorted(kiosk_dir.glob("*")):
            latest = source_dir / "latest.log"
            if not latest.is_file():
                continue
            chunks = source_dir / "chunks"
            stat = latest.stat()
            items.append(
                {
                    "kiosk_id": kiosk_dir.name,
                    "source": source_dir.name,
                    "latest_bytes": stat.st_size,
                    "updated_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
                    "chunks": len(list(chunks.glob("*.log"))) if chunks.is_dir() else 0,
                    "latest_url": f"/api/kiosk-logs/{kiosk_dir.name}/latest?source={source_dir.name}",
                }
            )
    return {"ok": True, "items": items}


@app.get("/api/kiosk-logs/{kiosk_id}/latest")
def latest_kiosk_log(
    kiosk_id: str,
    source: str = "srv_out.log",
    _: None = Depends(_check_api_key),
) -> FileResponse:
    path = _kiosk_log_dir(kiosk_id, source) / "latest.log"
    if not path.is_file():
        raise HTTPException(404, "Log not found")
    return FileResponse(path, media_type="text/plain; charset=utf-8", filename=path.name)


@app.websocket("/ws/kiosk-logs")
async def kiosk_logs_ws(websocket: WebSocket, key: str = "") -> None:
    if not _is_api_token_valid(key):
        await websocket.close(code=1008)
        return
    await log_ws_hub.connect(websocket)
    try:
        await websocket.send_json(
            {
                "type": "hello",
                "received_at": datetime.now(UTC).isoformat(),
                "message": "connected",
            }
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        log_ws_hub.disconnect(websocket)


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
