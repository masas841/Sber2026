"""Перекодирование в H.264 — воспроизведение в Chrome/Edge/Safari."""

import subprocess
from pathlib import Path


def ensure_browser_mp4(path: Path, fps: int) -> Path:
    """
    Конвертирует любой MP4 в H.264 + yuv420p + faststart.
    Браузеры не воспроизводят OpenCV mp4v (MPEG-4 Part 2).
    """
    from app.config import settings

    import imageio_ffmpeg

    src = path.resolve()
    tmp = src.with_suffix(".h264.mp4")
    crf = max(0, min(51, int(settings.video_encode_crf)))
    preset = (settings.video_encode_preset or "medium").strip()

    cmd = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-i",
        str(src),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "high",
        "-level",
        "4.1",
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-r",
        str(fps),
        "-movflags",
        "+faststart",
        "-an",
        str(tmp),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "ffmpeg error")[-2000:]
        raise RuntimeError(f"Не удалось перекодировать видео: {err}")

    if not tmp.exists() or tmp.stat().st_size < 1000:
        raise RuntimeError("Перекодирование дало пустой файл")

    src.unlink(missing_ok=True)
    tmp.rename(src)
    return src
