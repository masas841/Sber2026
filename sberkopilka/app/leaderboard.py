"""Таблица лидеров за календарный день (сброс в leaderboard_reset_hour)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from app.config import settings

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "kopilka.db"


@dataclass(frozen=True)
class LeaderEntry:
    rank: int
    player_name: str
    score: int
    created_at: str


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=5.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                score INTEGER NOT NULL,
                play_date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_scores_day_score ON scores (play_date, score DESC)"
        )
        conn.commit()


def _today_key() -> str:
    return date.today().isoformat()


def add_score(player_name: str, score: int) -> LeaderEntry:
    name = (player_name or "Гость").strip()[:24] or "Гость"
    now = datetime.now().isoformat(timespec="seconds")
    day = _today_key()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO scores (player_name, score, play_date, created_at) VALUES (?, ?, ?, ?)",
            (name, max(0, int(score)), day, now),
        )
        conn.commit()
        row_id = cur.lastrowid
        rank = conn.execute(
            """
            SELECT COUNT(*) + 1 FROM scores
            WHERE play_date = ? AND score > ?
            """,
            (day, score),
        ).fetchone()[0]
    return LeaderEntry(rank=rank, player_name=name, score=score, created_at=now)


def top_today(limit: int = 10) -> list[LeaderEntry]:
    day = _today_key()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT player_name, score, created_at
            FROM scores
            WHERE play_date = ?
            ORDER BY score DESC, created_at ASC
            LIMIT ?
            """,
            (day, limit),
        ).fetchall()
    return [
        LeaderEntry(rank=i + 1, player_name=r["player_name"], score=r["score"], created_at=r["created_at"])
        for i, r in enumerate(rows)
    ]


def config_for_client() -> dict:
    return {
        "game_duration_sec": settings.game_duration_sec,
        "joystick_deadzone": settings.joystick_deadzone,
        "leaderboard_day": _today_key(),
    }
