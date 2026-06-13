"""Пол, возраст и комплекция гостя по селфи (InsightFace + эвристики кадра)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import cv2
import numpy as np

logger = logging.getLogger(__name__)

Gender = Literal["male", "female"]
Build = Literal["slim", "medium", "full"]
AgeGroup = Literal["child", "adult", "senior"]

AGE_LABEL_RU: dict[AgeGroup, str] = {
    "child": "ребёнок",
    "adult": "взрослый",
    "senior": "пожилой",
}


@dataclass(frozen=True)
class GuestProfile:
    gender: Gender
    build: Build
    age_group: AgeGroup
    age_years: int | None
    confidence_gender: float
    confidence_build: float
    confidence_age: float
    face_count: int = 1

    def is_group(self) -> bool:
        return self.face_count > 1

    def label_ru(self) -> str:
        if self.is_group():
            n = self.face_count
            mod10, mod100 = n % 10, n % 100
            if mod10 == 1 and mod100 != 11:
                word = "человек"
            elif mod10 in (2, 3, 4) and mod100 not in (12, 13, 14):
                word = "человека"
            else:
                word = "человек"
            return f"группа, {n} {word} в кадре"
        g = "мужской" if self.gender == "male" else "женский"
        b = {"slim": "стройная", "medium": "средняя", "full": "крупная"}[self.build]
        age = AGE_LABEL_RU[self.age_group]
        if self.age_years is not None:
            age = f"{age} (~{self.age_years} лет)"
        return f"{g}, {age}, комплекция {b}"


_LIGHT_FACE_MODES = frozenset(
    {
        "nanobanana",
        "nano_banana",
        "festival_nanobanana",
        "nana_banana",
        "festival_toon",
        "toon",
        "portrait_toon",
    }
)


def _load_face_app():
    from app.config import settings

    mode = settings.generator_mode.lower()
    if mode in {"festival_portrait", "portrait", "portrait_still"}:
        from app.generators.keyframe_instantid import KeyframeInstantIDGenerator

        _, face_app = KeyframeInstantIDGenerator._load()
        return face_app

    if mode in _LIGHT_FACE_MODES:
        from app.face_analysis import get_face_app

        return get_face_app()

    from app.generators.ref_video import RefVideoGenerator

    RefVideoGenerator._load_models()
    return RefVideoGenerator._face_app


def _gender_from_face(face) -> tuple[Gender, float]:
    if getattr(face, "gender", None) is None:
        return "female", 0.5
    is_male = int(face.gender) == 1
    return ("male" if is_male else "female"), 0.85


def _age_from_face(face) -> tuple[AgeGroup, int | None, float]:
    from app.config import settings

    raw = getattr(face, "age", None)
    if raw is None:
        return "adult", None, 0.5

    years = int(round(float(raw)))
    child_max = settings.guest_age_child_max
    senior_min = settings.guest_age_senior_min

    if years <= child_max:
        return "child", years, 0.8
    if years >= senior_min:
        return "senior", years, 0.8
    return "adult", years, 0.75


def _build_from_frame(img: np.ndarray, face) -> tuple[Build, float]:
    h, w = img.shape[:2]
    x1, y1, x2, y2 = face.bbox.astype(float)
    face_w = max(x2 - x1, 1.0)
    face_h = max(y2 - y1, 1.0)
    face_area = face_w * face_h
    frame_area = max(w * h, 1.0)
    area_ratio = face_area / frame_area
    width_ratio = face_w / max(w, 1.0)
    aspect = face_w / face_h

    if width_ratio >= 0.42 or (area_ratio >= 0.22 and aspect >= 0.82):
        return "full", 0.7
    if width_ratio <= 0.30 and area_ratio <= 0.14:
        return "slim", 0.65
    if width_ratio <= 0.34 and aspect < 0.78:
        return "slim", 0.6
    return "medium", 0.55


def _face_bbox_area(face) -> float:
    x1, y1, x2, y2 = face.bbox.astype(float)
    return max(x2 - x1, 1.0) * max(y2 - y1, 1.0)


def _face_center_in_zone(face, frame_w: int, frame_h: int) -> bool:
    """Фоновые прохожие обычно мелкие и/или у края кадра, вне зоны стенда."""
    from app.config import settings

    x1, y1, x2, y2 = face.bbox.astype(float)
    cx = ((x1 + x2) / 2) / max(frame_w, 1)
    cy = ((y1 + y2) / 2) / max(frame_h, 1)
    center_w = max(0.0, min(1.0, float(settings.guest_face_center_width)))
    center_h = max(0.0, min(1.0, float(settings.guest_face_center_height)))
    x_min = (1.0 - center_w) / 2
    y_min = (1.0 - center_h) / 2
    return x_min <= cx <= 1.0 - x_min and y_min <= cy <= 1.0 - y_min


def _filter_group_faces(faces: list, img: np.ndarray) -> list:
    """Оставляем только крупных центральных гостей, а не фоновых прохожих."""
    from app.config import settings

    if len(faces) <= 1:
        return faces

    h, w = img.shape[:2]
    areas = [_face_bbox_area(f) for f in faces]
    max_area = max(areas)
    min_ratio = float(settings.guest_face_min_relative_size)
    kept = [
        f
        for f, area in zip(faces, areas)
        if area >= max_area * min_ratio and _face_center_in_zone(f, w, h)
    ]
    if not kept:
        kept = [max(faces, key=_face_bbox_area)]
    kept.sort(key=_face_bbox_area, reverse=True)
    if len(kept) < len(faces):
        logger.info(
            "guest_profile: отфильтровано %d фоновых лиц (min %.0f%% от крупнейшего, central %.0fx%.0f%%)",
            len(faces) - len(kept),
            min_ratio * 100,
            float(settings.guest_face_center_width) * 100,
            float(settings.guest_face_center_height) * 100,
        )
    return kept


def analyze_guest_image(image_path: Path) -> GuestProfile:
    face_app = _load_face_app()
    img = cv2.imread(str(image_path))
    if img is None:
        raise RuntimeError(f"Не удалось прочитать фото: {image_path}")

    faces = face_app.get(img)
    faces = _filter_group_faces(faces, img)
    if not faces:
        raise RuntimeError("На фото не найдено лицо")

    face = max(
        faces,
        key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
    )

    gender, g_conf = _gender_from_face(face)
    age_group, age_years, a_conf = _age_from_face(face)
    build, b_conf = _build_from_frame(img, face)
    profile = GuestProfile(
        gender=gender,
        build=build,
        age_group=age_group,
        age_years=age_years,
        confidence_gender=g_conf,
        confidence_build=b_conf,
        confidence_age=a_conf,
        face_count=len(faces),
    )
    if len(faces) > 1:
        logger.info("guest_profile: %s (главное лицо — крупнейшее)", profile.label_ru())
    else:
        logger.info("guest_profile: %s", profile.label_ru())
    return profile


def profile_to_dict(profile: GuestProfile) -> dict:
    return {
        "gender": profile.gender,
        "build": profile.build,
        "age_group": profile.age_group,
        "age_group_label": AGE_LABEL_RU[profile.age_group],
        "age_years": profile.age_years,
        "label": profile.label_ru(),
        "confidence_gender": profile.confidence_gender,
        "confidence_build": profile.confidence_build,
        "confidence_age": profile.confidence_age,
        "face_count": profile.face_count,
    }
