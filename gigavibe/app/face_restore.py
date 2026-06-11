"""
Восстановление лица после inswapper (GFPGAN, upscale=1, paste_back).
Требует: pip install gfpgan basicsr facexlib
"""

from __future__ import annotations

import logging
import sys
import urllib.request
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "models" / "gfpgan"
MODEL_PATH = MODEL_DIR / "GFPGANv1.4.pth"
MODEL_URLS = (
    "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.4/GFPGANv1.4.pth",
    "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth",
    "https://huggingface.co/grokcv/GFPGAN/resolve/main/GFPGANv1.4.pth",
)

_restorer = None


def _patch_torchvision_for_basicsr() -> None:
    """basicsr 1.4.x с torchvision >= 0.16."""
    if "torchvision.transforms.functional_tensor" in sys.modules:
        return
    import torchvision.transforms.functional as functional

    sys.modules["torchvision.transforms.functional_tensor"] = functional


def _download_model() -> None:
    import time

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    last_err: Exception | None = None
    for url in MODEL_URLS:
        for attempt in range(3):
            try:
                logger.info("Downloading GFPGANv1.4.pth from %s …", url)
                urllib.request.urlretrieve(url, MODEL_PATH)
                if MODEL_PATH.stat().st_size > 1_000_000:
                    return
            except Exception as exc:
                last_err = exc
                MODEL_PATH.unlink(missing_ok=True)
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(
        f"Не удалось скачать GFPGANv1.4.pth. Положите файл в {MODEL_PATH} "
        f"или запустите scripts\\download_gfpgan.ps1"
    ) from last_err


def _ensure_model() -> Path:
    if MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 1_000_000:
        return MODEL_PATH
    _download_model()
    return MODEL_PATH


def warmup_model() -> None:
    """Загрузить GFPGAN в VRAM при старте (резидентно между запросами)."""
    if is_available():
        _get_restorer()


def is_available() -> bool:
    try:
        _patch_torchvision_for_basicsr()
        from gfpgan import GFPGANer  # noqa: F401

        return True
    except Exception:
        return False


def _resolve_restore_device():
    """torch.device для GFPGAN по settings.ref_video_restore_device_id."""
    import torch

    from app.config import settings

    dev_id = int(settings.ref_video_restore_device_id)
    if dev_id >= 0:
        if torch.cuda.is_available() and dev_id < torch.cuda.device_count():
            return torch.device(f"cuda:{dev_id}")
        if torch.cuda.is_available():
            return torch.device("cuda:0")
        return torch.device("cpu")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def new_restorer():
    """Создаёт НОВЫЙ независимый экземпляр GFPGANer на restore-устройстве.

    Нужен для пула параллельных restore-воркеров: GFPGANer.face_helper хранит
    per-call состояние (all_landmarks_5, cropped_faces), поэтому один экземпляр
    НЕ потокобезопасен — каждому воркеру нужен свой. Веса модели одни и те же на
    диске, но сессии/буферы у каждого экземпляра свои.
    """
    _patch_torchvision_for_basicsr()
    from gfpgan import GFPGANer

    _ensure_model()
    device = _resolve_restore_device()
    r = GFPGANer(
        model_path=str(MODEL_PATH),
        upscale=1,
        arch="clean",
        channel_multiplier=2,
        bg_upsampler=None,
        device=device,
    )
    logger.info("GFPGAN instance ready on %s", device)
    return r


def _get_restorer():
    global _restorer
    if _restorer is not None:
        return _restorer
    _restorer = new_restorer()
    logger.info("GFPGAN ready (resident singleton)")
    return _restorer


def restore_frame_bgr(frame_bgr: np.ndarray, restorer=None) -> np.ndarray:
    r = restorer or _get_restorer()
    try:
        _, _, restored = r.enhance(
            frame_bgr,
            has_aligned=False,
            only_center_face=True,
            paste_back=True,
        )
        return restored
    except Exception as exc:
        logger.warning("GFPGAN frame skip: %s", exc)
        return frame_bgr


def _maybe_half(restorer, enable: bool) -> bool:
    """Один раз переводит GFPGAN-модуль в fp16 (tensor cores RTX). Идемпотентно.

    Возвращает фактический режим (True = forward в fp16). fp16 ускоряет самый
    дорогой этап на Ampere, но может давать NaN на отдельных слоях StyleGAN —
    поэтому по умолчанию выключен и включается ключом REF_VIDEO_RESTORE_FP16
    после A/B-проверки качества.
    """
    if not enable:
        return False
    if getattr(restorer, "_gv_fp16", False):
        return True
    try:
        restorer.gfpgan.half()
        restorer._gv_fp16 = True
        logger.info("GFPGAN forward switched to fp16")
        return True
    except Exception as exc:  # pragma: no cover
        logger.warning("GFPGAN fp16 switch failed (%s) — staying fp32", exc)
        return False


def restore_frame_with_landmarks(
    frame_bgr: np.ndarray,
    landmarks_5: np.ndarray,
    restorer=None,
    weight: float = 0.5,
    fp16: bool = False,
) -> np.ndarray:
    """GFPGAN по УЖЕ известным 5 точкам лица (из детекции свопа) — без RetinaFace.

    Воспроизводит GFPGANer.enhance(has_aligned=False, paste_back=True), но
    пропускает get_face_landmarks_5: выравнивание 512-кропа идёт по переданным
    landmarks_5 (тот же 5-точечный формат ArcFace, что у insightface kps). Это
    убирает повторную детекцию лица и второй проход по MP4 (приём Rope —
    энханс выровненного кропа в общем конвейере со свопом).

    landmarks_5 — np.ndarray (5,2): глаза, нос, углы рта (как kps insightface).
    fp16 — прогон gfpgan в half (быстрее на Ampere, см. _maybe_half).
    """
    import torch
    from basicsr.utils import img2tensor, tensor2img
    from torchvision.transforms.functional import normalize

    r = restorer or _get_restorer()
    use_fp16 = _maybe_half(r, fp16)
    fh = r.face_helper
    fh.clean_all()
    fh.read_image(frame_bgr)
    # Инъекция готовых точек вместо RetinaFace-детекции.
    fh.all_landmarks_5 = [np.asarray(landmarks_5, dtype=np.float32)]
    fh.align_warp_face()

    for cropped_face in fh.cropped_faces:
        t = img2tensor(cropped_face / 255.0, bgr2rgb=True, float32=True)
        normalize(t, (0.5, 0.5, 0.5), (0.5, 0.5, 0.5), inplace=True)
        t = t.unsqueeze(0).to(r.device)
        if use_fp16:
            t = t.half()
        try:
            with torch.no_grad():
                output = r.gfpgan(t, return_rgb=False, weight=weight)[0]
            restored = tensor2img(
                output.squeeze(0).float(), rgb2bgr=True, min_max=(-1, 1)
            )
            if not np.isfinite(restored).all():
                logger.warning("GFPGAN output non-finite (fp16?) — кадр без restore")
                restored = cropped_face
        except RuntimeError as exc:
            logger.warning("GFPGAN inline forward fail: %s", exc)
            restored = cropped_face
        fh.add_restored_face(restored.astype("uint8"))

    fh.get_inverse_affine(None)
    # parsenet-маска внутри paste_faces_to_input_image → мягкий шов.
    return fh.paste_faces_to_input_image(upsample_img=None)


def restore_frame_with_landmarks_residual(
    frame_bgr: np.ndarray,
    landmarks_5: np.ndarray,
    restorer=None,
    weight: float = 0.5,
    fp16: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """Инлайн-restore (как restore_frame_with_landmarks) + «детальный слой».

    Возвращает (restored_bgr_uint8, residual_float32), где
    residual = restored − исходный кадр. residual нужен для интерполяции на
    промежуточных кадрах при стрейдинге (REF_VIDEO_RESTORE_EVERY_N>1) —
    лицо между keyframe'ами почти не двигается, поэтому добавление
    интерполированного residual к свопнутому кадру даёт чёткость без прогона
    GFPGAN на каждом кадре.
    """
    restored = restore_frame_with_landmarks(
        frame_bgr, landmarks_5, restorer, weight, fp16
    )
    residual = restored.astype(np.float32) - frame_bgr.astype(np.float32)
    return restored, residual


def _restore_with_residual(frame_bgr: np.ndarray, restorer):
    """Полный GFPGAN + «детальный слой» (restored − original) для интерполяции."""
    restored = restore_frame_bgr(frame_bgr, restorer)
    residual = restored.astype(np.float32) - frame_bgr.astype(np.float32)
    return restored, residual


def _apply_residual(frame_bgr: np.ndarray, residual: np.ndarray) -> np.ndarray:
    out = frame_bgr.astype(np.float32) + residual
    return np.clip(out, 0.0, 255.0).astype(np.uint8)


def _restore_strided(cap, writer, restorer, every_n: int, interpolate: bool) -> tuple[int, int]:
    """
    Каждый every_n-й кадр (keyframe) проходит полный GFPGAN; для промежуточных
    добавляется интерполированный детальный слой соседних keyframe'ов.
    Возвращает (всего записано кадров, прогнано через GFPGAN).
    """
    prev_res: np.ndarray | None = None
    pending: list[np.ndarray] = []  # исходные промежуточные кадры между keyframe'ами
    read_idx = 0  # индекс прочитанного кадра — для выбора keyframe (% every_n)
    written = 0
    restored_count = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        if read_idx % every_n == 0:
            restored, residual = _restore_with_residual(frame, restorer)
            restored_count += 1
            # Долить накопленные промежуточные кадры между prev_res и текущим keyframe.
            if pending and prev_res is not None:
                span = len(pending) + 1
                for j, orig in enumerate(pending, start=1):
                    if interpolate:
                        t = j / span
                        res_j = prev_res * (1.0 - t) + residual * t
                    else:
                        res_j = prev_res
                    writer.write(_apply_residual(orig, res_j))
                    written += 1
                pending = []
            writer.write(restored)
            written += 1
            prev_res = residual
        else:
            pending.append(frame)

        read_idx += 1

    # Хвост после последнего keyframe — держим его residual.
    for orig in pending:
        writer.write(_apply_residual(orig, prev_res) if prev_res is not None else orig)
        written += 1

    return written, restored_count


def restore_video_faces(video_path: Path) -> Path:
    """Проходит по MP4 после swap и улучшает лицо.

    REF_VIDEO_RESTORE_EVERY_N>1 — полный GFPGAN только на каждом N-м кадре,
    промежуточные получают интерполированный детальный слой (быстрее в ~N раз).
    """
    if not is_available():
        raise RuntimeError(
            "GFPGAN не установлен. В venv: pip install gfpgan basicsr facexlib"
        )

    from app.config import settings

    every_n = max(int(settings.ref_video_restore_every_n), 1)
    interpolate = bool(settings.ref_video_restore_interpolate)

    restorer = _get_restorer()
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Не открыть видео: {video_path}")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 24.0)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    tmp = video_path.with_suffix(".gfpgan.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(tmp), fourcc, fps, (w, h))

    if every_n <= 1:
        n = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            writer.write(restore_frame_bgr(frame, restorer))
            n += 1
        restored_count = n
    else:
        n, restored_count = _restore_strided(
            cap, writer, restorer, every_n, interpolate
        )

    cap.release()
    writer.release()
    if n == 0:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("Видео без кадров для GFPGAN")

    from app.video_encode import ensure_browser_mp4

    video_path.unlink(missing_ok=True)
    tmp.rename(video_path)
    ensure_browser_mp4(video_path, max(int(round(fps)), 1))
    logger.info(
        "GFPGAN restored %s/%s frames (%dx%d, every_n=%s, interp=%s)",
        restored_count,
        n,
        w,
        h,
        every_n,
        interpolate,
    )
    return video_path
