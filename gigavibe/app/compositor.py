"""Финальная сборка: бренд-рамка, музыка (если есть)."""

from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def apply_overlay(video_path: Path, overlay_path: Path | None) -> Path:
    if overlay_path is None or not overlay_path.exists():
        return video_path

    overlay = Image.open(overlay_path).convert("RGBA")
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    overlay = overlay.resize((w, h), Image.Resampling.LANCZOS)
    ov = np.array(overlay)
    alpha = ov[:, :, 3:4] / 255.0
    ov_rgb = ov[:, :, :3][:, :, ::-1]

    tmp = video_path.with_suffix(".ov.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(tmp), fourcc, fps, (w, h))

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        blended = (frame * (1 - alpha) + ov_rgb * alpha).astype(np.uint8)
        writer.write(blended)

    cap.release()
    writer.release()
    video_path.unlink(missing_ok=True)
    tmp.rename(video_path)
    return video_path


def mux_audio(video_path: Path, audio_path: Path | None) -> Path:
    if audio_path is None or not audio_path.exists():
        return video_path

    try:
        import imageio_ffmpeg
    except ImportError:
        return video_path

    out = video_path.with_suffix(".audio.mp4")
    cmd = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        str(out),
    ]
    import subprocess

    subprocess.run(cmd, check=True, capture_output=True)
    video_path.unlink(missing_ok=True)
    out.rename(video_path)
    return video_path
