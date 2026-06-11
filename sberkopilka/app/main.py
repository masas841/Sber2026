import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import settings
from app.leaderboard import add_score, config_for_client, init_db, top_today

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"

app = FastAPI(title="SberKopilka", version="0.1.0")

init_db()

if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


class ScoreSubmit(BaseModel):
    player_name: str = Field(default="Гость", max_length=24)
    score: int = Field(ge=0, le=9_999_999)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "service": "sberkopilka"}


@app.get("/api/config")
def api_config() -> dict:
    return config_for_client()


@app.get("/api/leaderboard")
def api_leaderboard(limit: int = 10) -> dict:
    limit = max(1, min(limit, 50))
    entries = top_today(limit)
    return {
        "day": config_for_client()["leaderboard_day"],
        "entries": [
            {"rank": e.rank, "name": e.player_name, "score": e.score, "at": e.created_at}
            for e in entries
        ],
    }


@app.post("/api/leaderboard")
def api_submit(body: ScoreSubmit) -> dict:
    entry = add_score(body.player_name, body.score)
    return {
        "rank": entry.rank,
        "name": entry.player_name,
        "score": entry.score,
        "day": config_for_client()["leaderboard_day"],
    }


_NO_CACHE = {"Cache-Control": "no-store, no-cache, must-revalidate"}


@app.get("/")
def index() -> FileResponse:
    html = WEB_DIR / "index.html"
    if not html.exists():
        raise HTTPException(404, "index.html missing")
    return FileResponse(html, headers=_NO_CACHE)


MAZE_LAYOUT_PATH = WEB_DIR / "js" / "maze-layout.generated.json"
MAZE_LAYOUT_ASSETS = ROOT / "web" / "assets" / "figma" / "layouts" / "maze-from-figma.json"
SYNC_MAZE_SCRIPT = ROOT / "scripts" / "sync_maze_to_js.py"


def _cell_world(ox: float, oy: float, tw: float, th: float, gx: int, gy: int) -> tuple[float, float]:
    return round(ox + gx * tw + tw / 2, 2), round(oy + gy * th + th / 2, 2)


def _normalize_maze_layout(body: dict[str, Any]) -> dict[str, Any]:
    ox, oy = body["fieldOrigin"]
    cols = int(body["cols"])
    rows = int(body["rows"])
    field_w, field_h = body.get("fieldSize", [473, 492])
    tile_w = float(body.get("tileW", field_w / cols))
    tile_h = float(body.get("tileH", field_h / rows))
    body["fieldSize"] = [field_w, field_h]
    body["tileW"] = tile_w
    body["tileH"] = tile_h
    body["tile"] = float(body.get("tile", (tile_w + tile_h) / 2))

    ps = body["playerStart"]
    ps["wx"], ps["wy"] = _cell_world(ox, oy, tile_w, tile_h, int(ps["x"]), int(ps["y"]))
    for g in body.get("ghostSpawns", []):
        g["wx"], g["wy"] = _cell_world(ox, oy, tile_w, tile_h, int(g["x"]), int(g["y"]))
    if body.get("portfolioTile"):
        pt = body["portfolioTile"]
        pt["wx"], pt["wy"] = _cell_world(ox, oy, tile_w, tile_h, int(pt["x"]), int(pt["y"]))
    return body


def _sync_maze_js() -> None:
    subprocess.run([sys.executable, str(SYNC_MAZE_SCRIPT)], cwd=str(ROOT), check=True)


@app.get("/maze-editor")
def maze_editor() -> FileResponse:
    html = WEB_DIR / "maze-editor.html"
    if not html.exists():
        raise HTTPException(404, "maze-editor.html missing")
    return FileResponse(html, headers=_NO_CACHE)


@app.get("/api/maze-layout")
def get_maze_layout() -> dict[str, Any]:
    if not MAZE_LAYOUT_PATH.exists():
        raise HTTPException(404, "maze-layout.generated.json missing")
    return json.loads(MAZE_LAYOUT_PATH.read_text(encoding="utf-8"))


@app.put("/api/maze-layout")
def put_maze_layout(body: dict[str, Any]) -> dict[str, bool]:
    cols = int(body.get("cols", 16))
    rows = int(body.get("rows", 17))
    if cols < 4 or cols > 40 or rows < 4 or rows > 40:
        raise HTTPException(400, "cols and rows must be between 4 and 40")
    if "rows_ascii" not in body or len(body["rows_ascii"]) != rows:
        raise HTTPException(400, f"rows_ascii must be {rows} lines")
    for row in body["rows_ascii"]:
        if len(row) != cols or any(c not in "#." for c in row):
            raise HTTPException(400, f"each row must be {cols} chars of # and .")
    body = _normalize_maze_layout(body)
    text = json.dumps(body, ensure_ascii=False, indent=2)
    MAZE_LAYOUT_PATH.write_text(text, encoding="utf-8")
    MAZE_LAYOUT_ASSETS.parent.mkdir(parents=True, exist_ok=True)
    MAZE_LAYOUT_ASSETS.write_text(text, encoding="utf-8")
    try:
        _sync_maze_js()
    except subprocess.CalledProcessError as exc:
        raise HTTPException(500, f"sync_maze_to_js failed: {exc}") from exc
    return {"ok": True, "synced": True}


def run() -> None:
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    run()
