"""События киоска: визиты, старты и завершения игр, отправка в топ."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "kopilka.db"

ALLOWED_EVENTS = frozenset({"visit", "game_start", "game_finish", "score_submit"})


@dataclass(frozen=True)
class DayStats:
    day: str
    visits: int
    games_started: int
    games_finished: int
    scores_submitted: int
    unique_sessions_finished: int


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=5.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_log_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS log_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                event TEXT NOT NULL,
                play_date TEXT NOT NULL,
                score INTEGER,
                player_name TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_log_events_day ON log_events (play_date, event)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_log_events_session ON log_events (session_id, play_date)"
        )
        conn.commit()


def _today_key() -> str:
    return date.today().isoformat()


def log_event(
    *,
    session_id: str,
    event: str,
    score: int | None = None,
    player_name: str | None = None,
) -> None:
    sid = (session_id or "").strip()[:64]
    if not sid:
        raise ValueError("session_id required")
    ev = (event or "").strip()
    if ev not in ALLOWED_EVENTS:
        raise ValueError(f"unknown event: {ev}")

    now = datetime.now().isoformat(timespec="seconds")
    day = _today_key()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO log_events (session_id, event, play_date, score, player_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                sid,
                ev,
                day,
                max(0, int(score)) if score is not None else None,
                (player_name or None),
                now,
            ),
        )
        conn.commit()


def stats_for_day(day: str | None = None) -> DayStats:
    key = day or _today_key()
    with _connect() as conn:
        visits = conn.execute(
            "SELECT COUNT(DISTINCT session_id) FROM log_events WHERE play_date = ? AND event = 'visit'",
            (key,),
        ).fetchone()[0]
        games_started = conn.execute(
            "SELECT COUNT(*) FROM log_events WHERE play_date = ? AND event = 'game_start'",
            (key,),
        ).fetchone()[0]
        games_finished = conn.execute(
            "SELECT COUNT(*) FROM log_events WHERE play_date = ? AND event = 'game_finish'",
            (key,),
        ).fetchone()[0]
        scores_submitted = conn.execute(
            "SELECT COUNT(*) FROM log_events WHERE play_date = ? AND event = 'score_submit'",
            (key,),
        ).fetchone()[0]
        unique_sessions_finished = conn.execute(
            "SELECT COUNT(DISTINCT session_id) FROM log_events WHERE play_date = ? AND event = 'game_finish'",
            (key,),
        ).fetchone()[0]
    return DayStats(
        day=key,
        visits=visits,
        games_started=games_started,
        games_finished=games_finished,
        scores_submitted=scores_submitted,
        unique_sessions_finished=unique_sessions_finished,
    )


def stats_to_dict(stats: DayStats) -> dict[str, Any]:
    return {
        "day": stats.day,
        "visits": stats.visits,
        "games_started": stats.games_started,
        "games_finished": stats.games_finished,
        "scores_submitted": stats.scores_submitted,
        "unique_sessions_finished": stats.unique_sessions_finished,
    }
