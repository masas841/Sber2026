"""LivePortrait: селфи + driving-video -> анимированный портрет."""

from __future__ import annotations

import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from app.generators.base import VideoGenerator

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_LP_ROOT = ROOT / "vendor" / "LivePortrait"
DEFAULT_LP_VENV = ROOT / ".venv-liveportrait"
DEFAULT_DRIVING_DIR = ROOT / "assets" / "driving"
FFMPEG_DIR = ROOT / "tools" / "ffmpeg"


def _weight_marker(lp_root: Path) -> Path:
    return (
        lp_root
        / "pretrained_weights"
        / "liveportrait"
        / "base_models"
        / "appearance_feature_extractor.pth"
    )


def _resolve_lp_root() -> Path:
    from app.config import settings

    raw = getattr(settings, "liveportrait_root", None)
    if raw:
        p = Path(raw)
        return p if p.is_absolute() else (ROOT / p)
    return DEFAULT_LP_ROOT


def _resolve_lp_python() -> Path:
    from app.config import settings

    if settings.liveportrait_python:
        return Path(settings.liveportrait_python)
    if settings.liveportrait_use_main_venv:
        main_py = ROOT / ".venv" / "Scripts" / "python.exe"
        if main_py.exists():
            return main_py
    venv_py = DEFAULT_LP_VENV / "Scripts" / "python.exe"
    if venv_py.exists():
        return venv_py
    main_py = ROOT / ".venv" / "Scripts" / "python.exe"
    if main_py.exists():
        return main_py
    return Path(sys.executable)


def _ffmpeg_exe() -> str | None:
    for name in ("ffmpeg.exe", "ffmpeg"):
        p = FFMPEG_DIR / name
        if p.exists():
            return str(p)
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _pick_driving_video() -> Path:
    from app.config import settings

    if settings.liveportrait_driving_path:
        p = Path(settings.liveportrait_driving_path)
        if not p.is_absolute():
            p = ROOT / p
        if not p.exists():
            raise FileNotFoundError(f"LIVEPORTRAIT_DRIVING_PATH не найден: {p}")
        if settings.liveportrait_use_pkl_if_available:
            pkl = p.with_suffix(".pkl")
            if pkl.exists():
                return pkl
        return p

    dirs: list[Path] = []
    if settings.liveportrait_driving_dir:
        d = Path(settings.liveportrait_driving_dir)
        dirs.append(d if d.is_absolute() else ROOT / d)
    dirs.extend([DEFAULT_DRIVING_DIR, _resolve_lp_root() / "assets" / "examples" / "driving"])

    candidates: list[Path] = []
    for d in dirs:
        if not d.is_dir():
            continue
        if settings.liveportrait_use_pkl_if_available:
            candidates.extend(sorted(d.glob("*.pkl")))
        for ext in ("*.mp4", "*.MP4"):
            candidates.extend(sorted(d.glob(ext)))

    if not candidates:
        raise FileNotFoundError(
            "Нет driving-видео. Положите .mp4 или .pkl в assets/driving/"
        )

    if settings.liveportrait_random_drive and len(candidates) > 1:
        return random.choice(candidates)
    return candidates[0]


def _prepare_source_for_lp(source_image: Path, max_dim: int = 1280) -> Image.Image:
    """Оригинальные пропорции — LP сам кропит лицо (без принудительного 9:16)."""
    img = Image.open(source_image).convert("RGB")
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    return img


def _trim_driving_mp4(driving: Path, tmp_dir: Path, max_sec: float) -> Path:
    if driving.suffix.lower() == ".pkl" or max_sec <= 0:
        return driving
    ffmpeg = _ffmpeg_exe()
    if not ffmpeg:
        return driving
    clipped = tmp_dir / f"{driving.stem}_clip.mp4"
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(driving.resolve()),
        "-t",
        str(max_sec),
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(clipped),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0 and clipped.exists() and clipped.stat().st_size > 1000:
        return clipped
    return driving


def _basename_pair(source: Path, driving: Path) -> str:
    return f"{source.name}--{driving.name}"


def _fit_frame_bgr(frame: np.ndarray, width: int, height: int) -> np.ndarray:
    from app.video_fit import fit_frame_bgr

    return fit_frame_bgr(frame, width, height)


def _remux_to_kiosk(
    src_mp4: Path,
    output_path: Path,
    *,
    width: int,
    height: int,
    fps: int,
    duration_sec: float,
) -> Path:
    cap = cv2.VideoCapture(str(src_mp4))
    if not cap.isOpened():
        raise RuntimeError(f"Не удалось открыть видео LivePortrait: {src_mp4}")

    target_frames = max(int(fps * duration_sec), 1)
    raw_frames: list[np.ndarray] = []

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        raw_frames.append(frame)
    cap.release()

    if not raw_frames:
        raise RuntimeError("LivePortrait вернул пустое видео")

    # Равномерная выборка кадров (не «первые N») — меньше рывков при длинном driving
    if len(raw_frames) > target_frames:
        indices = np.linspace(0, len(raw_frames) - 1, target_frames, dtype=int)
        raw_frames = [raw_frames[i] for i in indices]
    elif len(raw_frames) < target_frames:
        raw_frames.extend([raw_frames[-1]] * (target_frames - len(raw_frames)))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    for frame in raw_frames:
        writer.write(_fit_frame_bgr(frame, width, height))
    writer.release()

    from app.video_encode import ensure_browser_mp4

    ensure_browser_mp4(output_path, fps)
    return output_path


class LivePortraitGenerator(VideoGenerator):
    @staticmethod
    def is_available() -> bool:
        lp_root = _resolve_lp_root()
        if not (lp_root / "inference.py").exists():
            return False
        if not _weight_marker(lp_root).exists():
            return False
        py = _resolve_lp_python()
        if not py.exists():
            return False
        try:
            r = subprocess.run(
                [str(py), "-c", "import torch; print(torch.cuda.is_available())"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(lp_root),
            )
            return r.returncode == 0 and "True" in (r.stdout or "")
        except (OSError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def install_hint() -> str:
        return "Запустите download_liveportrait.bat из папки gigavibe"

    def generate(
        self,
        source_image: Path,
        output_path: Path,
        *,
        width: int,
        height: int,
        fps: int,
        duration_sec: float,
    ) -> Path:
        from app.config import settings

        if not self.is_available():
            raise RuntimeError(
                "LivePortrait не готов. " + self.install_hint()
            )

        lp_root = _resolve_lp_root()
        lp_py = _resolve_lp_python()
        driving = _pick_driving_video()

        prepared = _prepare_source_for_lp(source_image)
        with tempfile.TemporaryDirectory(prefix="gigavibe_lp_") as tmp:
            tmp_path = Path(tmp)
            src_path = tmp_path / "source.jpg"
            prepared.save(src_path, format="JPEG", quality=95)

            driving_input = _trim_driving_mp4(
                driving, tmp_path, settings.liveportrait_driving_max_sec
            )

            out_dir = tmp_path / "out"
            out_dir.mkdir(parents=True, exist_ok=True)

            cmd = [
                str(lp_py),
                "inference.py",
                "-s",
                str(src_path.resolve()),
                "-d",
                str(driving_input.resolve()),
                "-o",
                str(out_dir.resolve()),
                "--device_id",
                str(settings.liveportrait_device_id),
                "--driving_option",
                settings.liveportrait_driving_option,
                "--driving_multiplier",
                str(settings.liveportrait_driving_multiplier),
                "--driving_smooth_observation_variance",
                str(settings.liveportrait_driving_smooth),
            ]
            if settings.liveportrait_flag_crop_driving_video and driving_input.suffix.lower() != ".pkl":
                cmd.append("--flag_crop_driving_video")
            if not settings.liveportrait_flag_stitching:
                cmd.append("--no_flag_stitching")
            if settings.liveportrait_flag_do_torch_compile:
                cmd.append("--flag_do_torch_compile")

            env = os.environ.copy()
            env.setdefault("PYTHONUTF8", "1")
            env.setdefault("PYTHONIOENCODING", "utf-8")
            env.setdefault("CI", "true")
            for ffmpeg_dir in (FFMPEG_DIR, lp_root / "ffmpeg"):
                if (ffmpeg_dir / "ffmpeg.exe").exists() or (ffmpeg_dir / "ffmpeg").exists():
                    env["PATH"] = str(ffmpeg_dir) + os.pathsep + env.get("PATH", "")
                    break

            result = subprocess.run(
                cmd,
                cwd=str(lp_root),
                env=env,
                capture_output=True,
                text=True,
                timeout=settings.liveportrait_timeout_sec,
            )
            if result.returncode != 0:
                tail = (result.stderr or result.stdout or "")[-3000:]
                raise RuntimeError(f"LivePortrait inference failed:\n{tail}")

            expected = out_dir / f"{_basename_pair(src_path, driving_input)}.mp4"
            if not expected.exists():
                mp4s = sorted(out_dir.glob("*.mp4"))
                mp4s = [p for p in mp4s if "_concat" not in p.name]
                if not mp4s:
                    raise RuntimeError(
                        f"LivePortrait не создал выходной mp4 в {out_dir}"
                    )
                expected = mp4s[0]

            _remux_to_kiosk(
                expected,
                output_path,
                width=width,
                height=height,
                fps=fps,
                duration_sec=duration_sec,
            )

        return output_path


def warmup_model() -> None:
    if not LivePortraitGenerator.is_available():
        raise RuntimeError(LivePortraitGenerator.install_hint())
