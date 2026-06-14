import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_logged_plays_count = -1
_TZ_OFFSETS: dict[str, timezone] = {
    "UTC": timezone.utc,
    "Europe/Moscow": timezone(timedelta(hours=3)),
}


def log_path() -> Path:
    raw = os.environ.get("PLAY_LOG_FILE", "").strip()
    if raw:
        return Path(raw)
    return ROOT / "data" / "plays.jsonl"


def log_tz() -> timezone:
    name = os.environ.get("PLAY_LOG_TZ", "Europe/Moscow").strip() or "Europe/Moscow"
    if name in _TZ_OFFSETS:
        return _TZ_OFFSETS[name]

    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(name)
    except Exception:
        return _TZ_OFFSETS["Europe/Moscow"]


def _count_lines() -> int:
    path = log_path()
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def logged_count() -> int:
    global _logged_plays_count
    if _logged_plays_count < 0:
        _logged_plays_count = _count_lines()
    return _logged_plays_count


def append_play(
    *,
    session_id: str,
    bytes_count: int,
    content_type: str,
    client_ip: str | None = None,
) -> dict:
    global _logged_plays_count

    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "bytes": bytes_count,
        "content_type": content_type,
    }
    if client_ip:
        record["client_ip"] = client_ip

    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    if _logged_plays_count < 0:
        _logged_plays_count = _count_lines()
    else:
        _logged_plays_count += 1

    return record


def _parse_ts(value: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def iter_plays() -> list[dict]:
    path = log_path()
    if not path.exists():
        return []

    plays: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                plays.append(item)
    return plays


def stats_for_date(date_str: str) -> dict:
    if not _DATE_RE.fullmatch(date_str):
        raise ValueError("date must be YYYY-MM-DD")

    tz = log_tz()
    count = 0
    for play in iter_plays():
        ts = play.get("ts")
        if not isinstance(ts, str):
            continue
        dt = _parse_ts(ts)
        if dt is None:
            continue
        if dt.astimezone(tz).strftime("%Y-%m-%d") == date_str:
            count += 1

    return {
        "date": date_str,
        "plays": count,
        "tz": str(tz),
    }


def stats_summary(*, days: int = 30) -> dict:
    tz = log_tz()
    by_date: dict[str, int] = {}

    for play in iter_plays():
        ts = play.get("ts")
        if not isinstance(ts, str):
            continue
        dt = _parse_ts(ts)
        if dt is None:
            continue
        day = dt.astimezone(tz).strftime("%Y-%m-%d")
        by_date[day] = by_date.get(day, 0) + 1

    ordered_dates = sorted(by_date.keys(), reverse=True)[:days]
    recent = {day: by_date[day] for day in ordered_dates}

    return {
        "total": sum(by_date.values()),
        "tz": str(tz),
        "by_date": recent,
    }
