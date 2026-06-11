"""Каталог референс-роликов: пол × возраст × комплекция → MP4 (случайный из списка)."""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path

from app.guest_profile import Build, GuestProfile

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
_BUILD_KEYS = frozenset({"slim", "medium", "full", "default"})
_VIDEO_SUFFIXES = {".mp4", ".mov", ".avi"}


def _resolve_path(raw: str) -> Path:
    p = Path(raw)
    if not p.is_absolute():
        p = ROOT / p
    return p


def _paths_from_entry(raw: str | list[str] | None) -> list[Path]:
    """Строка или массив путей → существующие файлы."""
    if raw is None:
        return []
    if isinstance(raw, str):
        items = [raw]
    elif isinstance(raw, list):
        items = [x for x in raw if isinstance(x, str) and x.strip()]
    else:
        return []

    found: list[Path] = []
    for item in items:
        p = _resolve_path(item)
        if p.exists() and p.suffix.lower() in _VIDEO_SUFFIXES:
            found.append(p)
    return found


def _pick_random(paths: list[Path]) -> Path | None:
    if not paths:
        return None
    return random.choice(paths)


def _is_build_map(node: dict) -> bool:
    return isinstance(node, dict) and bool(_BUILD_KEYS.intersection(node.keys()))


def _build_map_for_profile(gender_map: dict, profile: GuestProfile) -> dict:
    if not isinstance(gender_map, dict):
        return {}

    age_node = gender_map.get(profile.age_group)
    if _is_build_map(age_node):
        return age_node

    if _is_build_map(gender_map):
        return gender_map

    adult = gender_map.get("adult")
    if _is_build_map(adult):
        return adult

    return {}


def _pick_from_build_map(build_map: dict, profile: GuestProfile) -> Path | None:
    """Случайный ролик: свой build → medium → default внутри ячейки."""
    tiers: list[str] = [profile.build]
    if profile.build != "medium" and "medium" in build_map:
        tiers.append("medium")
    if "default" in build_map:
        tiers.append("default")

    for key in tiers:
        chosen = _pick_random(_paths_from_entry(build_map.get(key)))
        if chosen is not None:
            return chosen
    return None


def load_manifest(path: Path | None = None) -> dict:
    from app.config import settings

    manifest_path = path or settings.driving_manifest_path
    if not manifest_path.is_absolute():
        manifest_path = ROOT / manifest_path
    if not manifest_path.exists():
        return {"videos": {}, "default": None}
    with manifest_path.open(encoding="utf-8") as f:
        return json.load(f)


def pick_driving_video(profile: GuestProfile, manifest: dict | None = None) -> Path:
    from app.config import settings

    if manifest is None:
        manifest = load_manifest()

    videos = manifest.get("videos") or {}
    gender_map = videos.get(profile.gender) or {}
    build_map = _build_map_for_profile(gender_map, profile)

    chosen = _pick_from_build_map(build_map, profile)
    if chosen is not None:
        logger.info(
            "driving_catalog: %s/%s/%s -> %s (random)",
            profile.gender,
            profile.age_group,
            profile.build,
            chosen.name,
        )
        return chosen

    if isinstance(gender_map, dict):
        for age_key, node in gender_map.items():
            if age_key == profile.age_group or not _is_build_map(node):
                continue
            chosen = _pick_from_build_map(node, profile)
            if chosen is not None:
                logger.warning(
                    "driving_catalog: age fallback %s -> %s (random)",
                    age_key,
                    chosen.name,
                )
                return chosen

    chosen = _pick_random(_paths_from_entry(manifest.get("default")))
    if chosen is not None:
        return chosen

    if settings.liveportrait_driving_path:
        p = Path(settings.liveportrait_driving_path)
        if not p.is_absolute():
            p = ROOT / p
        if p.exists() and p.suffix.lower() in {".mp4", ".mov", ".avi", ".pkl"}:
            if p.suffix.lower() == ".pkl":
                for alt in (p.with_suffix(".MP4"), p.with_suffix(".mp4")):
                    if alt.exists():
                        return alt
            return p

    d = ROOT / "assets" / "driving"
    pool: list[Path] = []
    for ext in ("*.MP4", "*.mp4"):
        pool.extend(d.glob(ext))
    if pool:
        return random.choice(sorted(pool))

    raise FileNotFoundError(
        f"Нет ролика для {profile.gender}/{profile.age_group}/{profile.build}. "
        "Заполните assets/driving/manifest.json"
    )
