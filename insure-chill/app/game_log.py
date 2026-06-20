from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from threading import Lock
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import settings

ROOT = Path(__file__).resolve().parent.parent
LEGACY_LOG_PATH = ROOT / "data" / "games.jsonl"

_lock = Lock()


def log_path() -> Path:
    path = Path(settings.play_log_file or "data/plays.jsonl")
    return path if path.is_absolute() else ROOT / path


def _timezone() -> ZoneInfo | None:
    try:
        return ZoneInfo(settings.play_log_tz)
    except ZoneInfoNotFoundError:
        return None


def append_event(event: str, **fields: Any) -> dict[str, Any]:
    tz = _timezone()
    now = datetime.now(tz) if tz else datetime.now().astimezone()
    record: dict[str, Any] = {
        "ts": now.isoformat(timespec="seconds"),
        "event": event,
        **fields,
    }
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False)
    with _lock:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    return record


def read_events() -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    paths = [log_path()]
    if LEGACY_LOG_PATH != paths[0]:
        paths.append(LEGACY_LOG_PATH)

    for path in paths:
        if not path.exists():
            continue
        with _lock:
            for raw_line in path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return events


def _parse_ts(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _event_day(event: dict[str, Any]) -> date | None:
    ts = event.get("ts")
    if not isinstance(ts, str):
        return None
    parsed = _parse_ts(ts)
    if parsed is None:
        return None
    return parsed.date()


def stats_for_day(day: date | None = None) -> dict[str, Any]:
    target = day or date.today()
    starts = 0
    finishes = 0
    scores: list[int] = []

    for event in read_events():
        if _event_day(event) != target:
            continue
        name = event.get("event")
        if name == "start":
            starts += 1
        elif name == "finish":
            finishes += 1
            score = event.get("score")
            if isinstance(score, int):
                scores.append(score)

    return {
        "date": target.isoformat(),
        "starts": starts,
        "finishes": finishes,
        "avgScore": round(sum(scores) / len(scores), 2) if scores else None,
        "maxScore": max(scores) if scores else None,
    }


def summary(days: int = 7) -> list[dict[str, Any]]:
    today = date.today()
    return [
        stats_for_day(date.fromordinal(today.toordinal() - offset))
        for offset in range(days - 1, -1, -1)
    ]
