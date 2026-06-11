import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"

app = FastAPI(title="Smile Pay", version="0.1.0")

# Демо-хранилище сессий оплаты (in-memory)
_sessions: dict[str, dict] = {}

if WEB.exists():
    app.mount("/static", StaticFiles(directory=WEB), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "service": "smile-pay", "sessions": len(_sessions)}


@app.post("/api/capture")
async def capture(request: Request, photo: UploadFile = File(...)) -> dict:
    if photo.content_type and not photo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Expected an image upload")

    data = await photo.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty image")

    session_id = secrets.token_urlsafe(10)
    base = str(request.base_url).rstrip("/")
    pay_url = f"{base}/pay/{session_id}"
    _sessions[session_id] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "bytes": len(data),
        "content_type": photo.content_type or "image/jpeg",
    }

    return {
        "session_id": session_id,
        "pay_url": pay_url,
    }


@app.get("/pay/{session_id}", response_class=HTMLResponse)
def pay_page(session_id: str) -> HTMLResponse:
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Smile Pay</title>
  <style>
    body {{
      margin: 0; min-height: 100vh; display: grid; place-items: center;
      font-family: "Segoe UI", system-ui, sans-serif;
      background: linear-gradient(145deg, #3fd05a, #21a038 40%, #0d8523);
      color: #fff;
    }}
    .card {{
      text-align: center; padding: 2rem 2.5rem; border-radius: 24px;
      background: rgba(255,255,255,0.14); backdrop-filter: blur(12px);
      max-width: 360px;
    }}
    h1 {{ font-size: 1.5rem; margin: 0 0 0.5rem; }}
    p {{ margin: 0; opacity: 0.92; line-height: 1.45; }}
    code {{ font-size: 0.75rem; opacity: 0.7; word-break: break-all; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Оплата улыбкой</h1>
    <p>Самый сочный бургер на фудкорте — оплачен вашей улыбкой.</p>
    <p style="margin-top:1rem"><code>{session_id}</code></p>
  </div>
</body>
</html>"""
    return HTMLResponse(html)


def run() -> None:
    import os
    import uvicorn

    ssl_kwargs: dict = {}
    use_https = os.environ.get("USE_HTTPS", "").strip().lower() in {"1", "true", "yes", "on"}
    certfile = os.environ.get("SSL_CERTFILE")
    keyfile = os.environ.get("SSL_KEYFILE")
    if use_https and certfile and keyfile:
        cert = Path(certfile)
        key = Path(keyfile)
        if cert.exists() and key.exists():
            ssl_kwargs = {
                "ssl_certfile": str(cert),
                "ssl_keyfile": str(key),
            }
            print(f"[Smile Pay] HTTPS enabled: {cert}", flush=True)
        else:
            print(
                f"[Smile Pay] WARN: USE_HTTPS=true, но сертификат не найден "
                f"({cert} / {key}). Запуск по HTTP.",
                flush=True,
            )

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8888"))
    uvicorn.run("app.main:app", host=host, port=port, reload=False, **ssl_kwargs)


if __name__ == "__main__":
    run()
