"""Состояние «инсталляции выключены» для киосков фестиваля."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import settings

ACTIVITIES: dict[str, str] = {
    "gigavibe": "ГИГАвайб",
    "sberkopilka": "ИнвестКопилка",
    "insure-chill": "Застрахуй свой чилл",
    "smile-pay": "Smile Pay",
}


def _state_path() -> Path:
    return settings.data_dir / "kiosk_install_mode.json"


def _default_payload() -> dict[str, Any]:
    return {
        "version": 1,
        "updated_at": datetime.now(UTC).isoformat(),
        "activities": {key: False for key in ACTIVITIES},
    }


def _read_raw() -> dict[str, Any]:
    path = _state_path()
    if not path.is_file():
        return _default_payload()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _default_payload()
    if not isinstance(data, dict):
        return _default_payload()
    activities = data.get("activities")
    if not isinstance(activities, dict):
        activities = {}
    merged = {key: bool(activities.get(key, False)) for key in ACTIVITIES}
    return {
        "version": 1,
        "updated_at": str(data.get("updated_at") or datetime.now(UTC).isoformat()),
        "activities": merged,
    }


def read_state() -> dict[str, Any]:
    return _read_raw()


def write_state(activities: dict[str, bool]) -> dict[str, Any]:
    payload = {
        "version": 1,
        "updated_at": datetime.now(UTC).isoformat(),
        "activities": {
            key: bool(activities.get(key, False)) for key in ACTIVITIES
        },
    }
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def activity_state(activity_id: str) -> dict[str, Any]:
    if activity_id not in ACTIVITIES:
        raise KeyError(activity_id)
    state = _read_raw()
    install_off = bool(state["activities"].get(activity_id, False))
    return {
        "activity": activity_id,
        "label": ACTIVITIES[activity_id],
        "install_off": install_off,
        "updated_at": state["updated_at"],
    }
