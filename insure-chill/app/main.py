from pathlib import Path
from typing import Any, Literal

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"
IMG_DIR = ROOT / "img"

Role = Literal["screen", "control"]

app = FastAPI(title="Insure Chill", version="0.1.0")

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if IMG_DIR.exists():
    app.mount("/img", StaticFiles(directory=IMG_DIR), name="img")

_NO_CACHE = {"Cache-Control": "no-store, no-cache, must-revalidate"}


class ConnectionHub:
    def __init__(self) -> None:
        self.screen: set[WebSocket] = set()
        self.control: set[WebSocket] = set()
        self.state: dict[str, Any] = {
            "phase": "idle",
            "score": 0,
            "remaining": settings.game_duration_sec,
            "round": 0,
            "lastEvent": None,
        }

    async def connect(self, websocket: WebSocket, role: Role) -> None:
        await websocket.accept()
        self._bucket(role).add(websocket)
        await websocket.send_json(
            {
                "type": "hello",
                "role": role,
                "state": self.state,
                "config": client_config(),
            }
        )
        await self.broadcast(
            "presence",
            {
                "screens": len(self.screen),
                "controls": len(self.control),
            },
        )

    async def disconnect(self, websocket: WebSocket, role: Role) -> None:
        self._bucket(role).discard(websocket)
        await self.broadcast(
            "presence",
            {
                "screens": len(self.screen),
                "controls": len(self.control),
            },
        )

    async def handle(self, role: Role, message: dict[str, Any]) -> None:
        message_type = str(message.get("type", ""))
        if role == "control":
            await self._handle_control(message_type)
            return

        if message_type == "state":
            payload = dict(message.get("payload") or {})
            self.state.update(payload)
            await self.broadcast("state", self.state, target="control")
            return

        if message_type == "event":
            payload = dict(message.get("payload") or {})
            self.state["lastEvent"] = payload
            for key in ("phase", "score", "remaining"):
                if key in payload:
                    self.state[key] = payload[key]
            await self.broadcast("event", payload, target="control")
            return

    async def broadcast(self, message_type: str, payload: Any, target: Role | None = None) -> None:
        recipients: list[WebSocket]
        if target == "screen":
            recipients = list(self.screen)
        elif target == "control":
            recipients = list(self.control)
        else:
            recipients = [*self.screen, *self.control]

        stale: list[tuple[WebSocket, Role]] = []
        for websocket in recipients:
            try:
                await websocket.send_json({"type": message_type, "payload": payload})
            except RuntimeError:
                stale.append((websocket, "screen" if websocket in self.screen else "control"))

        for websocket, role in stale:
            self._bucket(role).discard(websocket)

    async def _handle_control(self, message_type: str) -> None:
        if message_type == "start":
            self.state = {
                "phase": "playing",
                "score": 0,
                "remaining": settings.game_duration_sec,
                "round": self.state.get("round", 0) + 1,
                "lastEvent": {"kind": "start"},
            }
            await self.broadcast("command", {"command": "start", "state": self.state}, target="screen")
            await self.broadcast("state", self.state, target="control")
            return

        if message_type == "insure":
            await self.broadcast("command", {"command": "insure"}, target="screen")
            return

        if message_type == "reset":
            self.state = {
                "phase": "idle",
                "score": 0,
                "remaining": settings.game_duration_sec,
                "round": self.state.get("round", 0),
                "lastEvent": {"kind": "reset"},
            }
            await self.broadcast("command", {"command": "reset", "state": self.state}, target="screen")
            await self.broadcast("state", self.state, target="control")

    def _bucket(self, role: Role) -> set[WebSocket]:
        return self.screen if role == "screen" else self.control


hub = ConnectionHub()


def client_config() -> dict[str, int]:
    return {
        "gameDurationSec": settings.game_duration_sec,
        "hitPaddingPx": settings.hit_padding_px,
    }


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "insure-chill",
        "screens": len(hub.screen),
        "controls": len(hub.control),
    }


@app.get("/api/config")
def api_config() -> dict[str, int]:
    return client_config()


@app.get("/")
def index() -> FileResponse:
    html = STATIC_DIR / "index.html"
    if not html.exists():
        raise HTTPException(status_code=404, detail="index.html missing")
    return FileResponse(html, headers=_NO_CACHE)


@app.get("/control")
def control() -> FileResponse:
    html = STATIC_DIR / "control.html"
    if not html.exists():
        raise HTTPException(status_code=404, detail="control.html missing")
    return FileResponse(html, headers=_NO_CACHE)


@app.websocket("/ws/{role}")
async def websocket_endpoint(websocket: WebSocket, role: str) -> None:
    if role not in {"screen", "control"}:
        await websocket.close(code=1008)
        return

    typed_role: Role = "screen" if role == "screen" else "control"
    await hub.connect(websocket, typed_role)
    try:
        while True:
            message = await websocket.receive_json()
            await hub.handle(typed_role, message)
    except WebSocketDisconnect:
        await hub.disconnect(websocket, typed_role)


def run() -> None:
    import os

    ssl_kwargs: dict = {}
    use_https = os.environ.get("USE_HTTPS", "").strip().lower() in {"1", "true", "yes", "on"}
    certfile = os.environ.get("SSL_CERTFILE")
    keyfile = os.environ.get("SSL_KEYFILE")
    if use_https and certfile and keyfile:
        cert = Path(certfile)
        key = Path(keyfile)
        if cert.is_absolute():
            cert_path = cert
            key_path = key
        else:
            cert_path = ROOT / cert
            key_path = ROOT / key
        if cert_path.exists() and key_path.exists():
            ssl_kwargs = {
                "ssl_certfile": str(cert_path),
                "ssl_keyfile": str(key_path),
            }
            print(f"[Insure Chill] HTTPS enabled: {cert_path}", flush=True)
        else:
            print(
                f"[Insure Chill] WARN: USE_HTTPS=true, но сертификат не найден "
                f"({cert_path} / {key_path}). Запуск по HTTP.",
                flush=True,
            )

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        **ssl_kwargs,
    )


if __name__ == "__main__":
    run()
