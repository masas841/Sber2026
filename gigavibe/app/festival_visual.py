"""
Визуальный слой «фестивальный ГИГАвайб» по ТЗ PDF:
  1) Собрать кадр: человек + праздничный фон (шары, неон, толпа-абстракция)
  2) После генерации — живая атмосфера (частицы, пульс света)
  3) Декоративная рамка как на слайдах (зелёная обводка, розовые акценты)
"""

from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

# Палитра Сбера на фестивале (слайды)
GREEN = (33, 160, 56)
PINK = (255, 79, 163)
CYAN = (94, 220, 240)
YELLOW = (255, 220, 60)
BLUE = (40, 120, 255)


def compose_festival_still(image: Image.Image, width: int, height: int) -> Image.Image:
    """
    Статичный «вайб»-кадр до LTX: чёткий портрет в центре + анимированный позже фон.
    Так модель меняет не только лицо, а всю сцену (шары, огни, глубину).
    """
    base = image.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)

    bg = base.copy()
    bg = ImageEnhance.Color(bg).enhance(1.45)
    bg = ImageEnhance.Contrast(bg).enhance(1.12)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=max(width, height) // 18))

    canvas = Image.new("RGB", (width, height), (180, 245, 200))
    grad = Image.new("RGB", (width, height))
    gdraw = ImageDraw.Draw(grad)
    for y in range(height):
        t = y / max(height - 1, 1)
        r = int(120 + 80 * (1 - t))
        g = int(220 + 30 * t)
        b = int(200 + 40 * (1 - t))
        gdraw.line([(0, y), (width, y)], fill=(r, g, b))
    canvas = Image.blend(canvas, grad, 0.55)
    canvas = Image.blend(canvas, bg, 0.72)

    draw = ImageDraw.Draw(canvas)
    rng = np.random.default_rng(42)
    for _ in range(14):
        cx = int(rng.integers(-width // 8, width))
        cy = int(rng.integers(0, height // 2))
        rw = int(rng.integers(width // 10, width // 5))
        rh = int(rw * rng.uniform(1.1, 1.35))
        color = (PINK, CYAN, YELLOW, BLUE, GREEN)[int(rng.integers(0, 5))]
        draw.ellipse([cx - rw, cy - rh, cx + rw, cy + rh], fill=color)

    # Овальная маска портрета (как кольца на слайде)
    mask = Image.new("L", (width, height), 0)
    mdraw = ImageDraw.Draw(mask)
    pad_x, pad_y = int(width * 0.14), int(height * 0.12)
    mdraw.ellipse([pad_x, pad_y, width - pad_x, height - pad_y], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=8))
    sharp = ImageEnhance.Sharpness(base).enhance(1.15)
    canvas.paste(sharp, (0, 0), mask)

    # Неоновые кольца (статичные — LTX оживит блики)
    ring = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    rdraw = ImageDraw.Draw(ring)
    for i, col in enumerate([PINK, GREEN, CYAN]):
        inset = 8 + i * 10
        rdraw.ellipse(
            [inset, inset, width - inset, height - inset],
            outline=(*col, 200),
            width=5,
        )
    canvas = Image.alpha_composite(canvas.convert("RGBA"), ring).convert("RGB")
    return canvas


def _balloon_positions(frame_idx: int, total: int, width: int, height: int, seed: int = 0) -> list[tuple[int, int, int, int, tuple[int, int, int]]]:
    rng = np.random.default_rng(seed)
    balloons = []
    n = 10
    for i in range(n):
        phase = (frame_idx / max(total, 1)) * math.pi * 2 + i * 0.7
        cx = int((0.15 + 0.7 * (i / n)) * width + math.sin(phase) * width * 0.04)
        cy = int((0.08 + (i % 4) * 0.06) * height + math.cos(phase * 0.9) * height * 0.03)
        rw = int(width * (0.06 + (i % 3) * 0.015))
        rh = int(rw * 1.2)
        color = (PINK, CYAN, YELLOW, BLUE, GREEN)[i % 5]
        balloons.append((cx, cy, rw, rh, color))
    return balloons


def _apply_frame_atmosphere(frame_bgr: np.ndarray, frame_idx: int, total: int) -> np.ndarray:
    h, w = frame_bgr.shape[:2]
    t = frame_idx / max(total - 1, 1)

    # Пульс фестивальных огней
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * (1.12 + 0.08 * math.sin(t * math.pi * 4)), 0, 255)
    hsv[:, :, 2] = np.clip(hsv[:, :, 2] * (1.05 + 0.06 * math.sin(t * math.pi * 2 + 1)), 0, 255)
    out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)

    # Лёгкий зум «дыхания» кадра
    scale = 1.0 + 0.03 * math.sin(t * math.pi * 2)
    nh, nw = int(h / scale), int(w / scale)
    y1 = (h - nh) // 2
    x1 = (w - nw) // 2
    cropped = out[y1 : y1 + nh, x1 : x1 + nw]
    out = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

    overlay = out.copy()
    for cx, cy, rw, rh, color in _balloon_positions(frame_idx, total, w, h):
        cv2.ellipse(
            overlay,
            (cx, cy),
            (rw, rh),
            angle=int(20 * math.sin(t * 6 + cx)),
            startAngle=0,
            endAngle=360,
            color=color[::-1],
            thickness=-1,
            lineType=cv2.LINE_AA,
        )
        cv2.ellipse(
            overlay,
            (cx - rw // 3, cy - rh // 2),
            (max(rw // 5, 2), max(rh // 8, 2)),
            0,
            0,
            360,
            (255, 255, 255),
            -1,
            cv2.LINE_AA,
        )

    # Шары только по краям — не перекрывать центр (портрет)
    center = np.zeros((h, w), dtype=np.float32)
    cv2.ellipse(center, (w // 2, h // 2), (int(w * 0.32), int(h * 0.38)), 0, 0, 360, 0, -1)
    edge_mask = 1.0 - center
    edge_mask = cv2.GaussianBlur(edge_mask, (0, 0), sigmaX=w // 16)
    blend = edge_mask[..., None] * 0.55
    out = np.clip(out * (1 - blend) + overlay * blend, 0, 255).astype(np.uint8)

    # Конфетти
    rng = np.random.default_rng(frame_idx + 7)
    for _ in range(18):
        x = int(rng.integers(0, w))
        y = int((rng.random() * h + frame_idx * h * 0.08) % h)
        c = (PINK, GREEN, CYAN, YELLOW)[int(rng.integers(0, 4))]
        cv2.circle(out, (x, y), int(rng.integers(2, 5)), c[::-1], -1, cv2.LINE_AA)

    # Световые блики по углам
    glow = np.zeros_like(out, dtype=np.float32)
    pulse = 0.35 + 0.25 * math.sin(t * math.pi * 3)
    cv2.circle(glow, (0, 0), int(w * 0.45), (180, 255, 120), -1)
    cv2.circle(glow, (w, 0), int(w * 0.35), (255, 120, 200), -1)
    out = np.clip(out.astype(np.float32) + glow * pulse * 0.25, 0, 255).astype(np.uint8)

    return out


def apply_festival_atmosphere(video_path: Path, fps: float) -> Path:
    """Усиливает «атмосферность» поверх выхода LTX/SVD."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return video_path

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if frame_count < 1:
        cap.release()
        return video_path

    tmp = video_path.with_suffix(".atm.mp4")
    writer = cv2.VideoWriter(str(tmp), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        writer.write(_apply_frame_atmosphere(frame, idx, frame_count))
        idx += 1
    cap.release()
    writer.release()

    from app.video_encode import ensure_browser_mp4

    video_path.unlink(missing_ok=True)
    tmp.rename(video_path)
    ensure_browser_mp4(video_path, int(fps))
    return video_path


def build_festival_frame_overlay(width: int, height: int) -> Image.Image:
    """Декоративная рамка (прозрачный центр) — слайд «атмосферная рамка»."""
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    border = max(10, width // 45)
    draw.rounded_rectangle(
        [border, border, width - border, height - border],
        radius=width // 20,
        outline=(*GREEN, 255),
        width=border,
    )

    # Розовый «цветок» сверху
    cx, cy = width // 2, border * 3
    for i in range(6):
        a = i * math.pi / 3
        px = cx + int(math.cos(a) * width * 0.09)
        py = cy + int(math.sin(a) * width * 0.05)
        draw.ellipse(
            [px - 22, py - 14, px + 22, py + 14],
            fill=(*PINK, 230),
        )

    # Шашечки сбоку
    check_h = height // 5
    check_y = height // 3
    sq = width // 28
    for row in range(check_h // sq):
        for col in range(6):
            x = width - border - 6 * sq + col * sq
            y = check_y + row * sq
            if (row + col) % 2 == 0:
                draw.rectangle([x, y, x + sq, y + sq], fill=(20, 20, 20, 220))

    # Голубая «кисть» снизу
    draw.ellipse(
        [width // 4, height - border * 8, width - width // 6, height - border],
        fill=(*CYAN, 180),
    )
    draw.ellipse(
        [width // 6, height - border * 5, width // 2, height - border * 2],
        fill=(*GREEN, 160),
    )

    # Розовая спираль-акцент
    spiral_cx = width - border * 4
    spiral_cy = height // 2
    for i in range(12):
        r = 8 + i * 3
        a = i * 0.55
        draw.ellipse(
            [
                spiral_cx + int(math.cos(a) * r) - 4,
                spiral_cy + int(math.sin(a) * r) - 4,
                spiral_cx + int(math.cos(a) * r) + 4,
                spiral_cy + int(math.sin(a) * r) + 4,
            ],
            fill=(*PINK, 200),
        )

    # Внутренняя мягкая виньетка по краям (центр остаётся прозрачным для видео)
    vignette = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    vdraw = ImageDraw.Draw(vignette)
    pad_x, pad_y = int(width * 0.1), int(height * 0.08)
    vdraw.ellipse([pad_x, pad_y, width - pad_x, height - pad_y], fill=(0, 0, 0, 0))
    outer = Image.new("RGBA", (width, height), (30, 180, 80, 35))
    mask = Image.new("L", (width, height), 255)
    mdraw = ImageDraw.Draw(mask)
    mdraw.ellipse([pad_x, pad_y, width - pad_x, height - pad_y], fill=0)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=width // 25))
    overlay = Image.composite(overlay, outer, mask)

    return overlay


def ensure_festival_frame_asset(width: int, height: int) -> Path:
    ASSETS.mkdir(parents=True, exist_ok=True)
    path = ASSETS / f"festival_frame_{width}x{height}.png"
    if not path.exists():
        build_festival_frame_overlay(width, height).save(path)
    return path
