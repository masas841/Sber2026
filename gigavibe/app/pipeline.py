import logging
import shutil
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from app.compositor import apply_overlay, mux_audio
from app.festival_visual import apply_festival_atmosphere, ensure_festival_frame_asset
from app.config import settings
from app.generators.factory import get_generator
from app.qr_util import save_job_qr

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


@dataclass
class Job:
    id: str
    status: JobStatus
    message: str = ""
    output_filename: str | None = None
    guest_gender: str | None = None
    guest_build: str | None = None
    guest_age_group: str | None = None
    guest_age_years: int | None = None
    driving_video: str | None = None
    total_sec: float | None = None
    generation_sec: float | None = None
    stage_timings: dict[str, float] = field(default_factory=dict)
    upload_ok: bool | None = None
    upload_error: str | None = None
    print_ok: bool | None = None
    print_error: str | None = None


_jobs: dict[str, Job] = {}
_ref_video_job_lock = threading.Lock()

PORTRAIT_MODES = frozenset(
    {
        "festival_portrait",
        "portrait",
        "portrait_still",
        "festival_toon",
        "toon",
        "portrait_toon",
        "nanobanana",
        "nano_banana",
        "festival_nanobanana",
        "nana_banana",
    }
)


def _stage_done(job: Job, timings: dict[str, float], name: str, t0: float) -> None:
    sec = time.perf_counter() - t0
    timings[name] = sec
    job.stage_timings = dict(timings)
    logger.info("job %s — %s: %.2f с", job.id, name, sec)


def get_job(job_id: str) -> Job | None:
    return _jobs.get(job_id)


def _job_dir(job_id: str) -> Path:
    return settings.data_dir / "jobs" / job_id


def create_job_from_upload(file_bytes: bytes, filename: str) -> str:
    job_id = uuid.uuid4().hex[:12]
    job_path = _job_dir(job_id)
    job_path.mkdir(parents=True, exist_ok=True)

    ext = Path(filename).suffix.lower() or ".jpg"
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        ext = ".jpg"
    source = job_path / f"source{ext}"
    source.write_bytes(file_bytes)

    _jobs[job_id] = Job(id=job_id, status=JobStatus.QUEUED)
    return job_id


def process_job(job_id: str) -> None:
    job = _jobs.get(job_id)
    if job is None:
        return

    mode = settings.generator_mode.lower()
    if mode in {"ref_video", "refvideo", "faceswap"} and settings.ref_video_serialize_jobs:
        acquired = _ref_video_job_lock.acquire(blocking=False)
        if not acquired:
            job.message = "Ждём свободный ref_video конвейер…"
            _ref_video_job_lock.acquire()
        try:
            _process_job_impl(job_id)
        finally:
            _ref_video_job_lock.release()
        return

    _process_job_impl(job_id)


def _process_job_impl(job_id: str) -> None:
    job = _jobs.get(job_id)
    if job is None:
        return

    job.status = JobStatus.PROCESSING
    mode = settings.generator_mode.lower()
    if mode == "ltx":
        from app.ltx_quality import resolve_ltx_quality

        q = resolve_ltx_quality(settings)
        job.message = f"LTX-Video ({settings.ltx_quality}): {q.hint}…"
    elif mode == "liveportrait":
        job.message = "LivePortrait: оживляем портрет…"
    elif mode in {"ref_video", "refvideo", "faceswap"}:
        job.message = ""
    elif mode in PORTRAIT_MODES:
        if mode in {"nanobanana", "nano_banana", "festival_nanobanana", "nana_banana"}:
            job.message = "Nano Banana: готовим портрет…"
        else:
            job.message = "Готовим фестивальный портрет…"
    else:
        job.message = "Собираем фестивальный вайб…"

    job_path = _job_dir(job_id)
    sources = list(job_path.glob("source.*"))
    if not sources:
        job.status = JobStatus.ERROR
        job.message = "Исходное фото не найдено"
        return

    source = sources[0]
    out_ext = ".jpg" if mode in {"nanobanana", "nano_banana", "festival_nanobanana", "nana_banana"} else (
        ".png" if mode in PORTRAIT_MODES else ".mp4"
    )
    out_name = f"{job_id}{out_ext}"
    output = settings.data_dir / "outputs" / out_name

    gen_sec: float | None = None
    guest_profile = None
    timings: dict[str, float] = {}
    t_job = time.perf_counter()
    try:
        if mode in {"ref_video", "refvideo", "faceswap"} or mode in PORTRAIT_MODES:
            from app.guest_profile import analyze_guest_image

            job.message = "Узнаём вас в кадре…"
            t0 = time.perf_counter()
            guest_profile = analyze_guest_image(source)
            _stage_done(job, timings, "guest_profile", t0)
            job.guest_gender = guest_profile.gender
            job.guest_build = guest_profile.build
            job.guest_age_group = guest_profile.age_group
            job.guest_age_years = guest_profile.age_years
            if mode in PORTRAIT_MODES:
                if mode in {"nanobanana", "nano_banana", "festival_nanobanana", "nana_banana"}:
                    job.message = f"Nano Banana: {guest_profile.label_ru()}…"
                else:
                    job.message = f"Стилизуем портрет: {guest_profile.label_ru()}…"
            else:
                job.message = f"Подбираем ролик: {guest_profile.label_ru()}…"

        generator = get_generator()
        if mode in PORTRAIT_MODES:
            gen_key = "portrait"
        elif mode in {"ref_video", "refvideo", "faceswap"}:
            gen_key = "face_swap"
        else:
            gen_key = "generation"
        job.message = (
            "Подменяем лицо в ролике…"
            if gen_key == "face_swap"
            else "Отправляем в Nano Banana…"
            if mode in {"nanobanana", "nano_banana", "festival_nanobanana", "nana_banana"}
            else "Генерируем фестивальный портрет…"
            if gen_key == "portrait"
            else job.message or "Генерируем видео…"
        )
        t_gen = time.perf_counter()
        gen_kwargs: dict = {
            "width": settings.video_width,
            "height": settings.video_height,
            "fps": settings.video_fps,
            "duration_sec": settings.video_duration_sec,
        }
        if guest_profile is not None:
            gen_kwargs["guest_profile"] = guest_profile

        generator.generate(source, output, **gen_kwargs)
        _stage_done(job, timings, gen_key, t_gen)
        gen_sec = timings[gen_key]
        last = getattr(generator, "last_generation_sec", None)
        if last is not None:
            gen_sec = float(last)
            timings[gen_key] = gen_sec
            job.stage_timings = dict(timings)

        ref_stages = getattr(generator, "last_stage_timings", None)
        if ref_stages and gen_key == "portrait":
            iid = float(ref_stages.get("instantid_s") or 0)
            if iid > 0:
                timings["portrait"] = iid
            job.stage_timings = dict(timings)
        elif ref_stages:
            rs = float(ref_stages.get("restore_s") or 0)
            ss = float(ref_stages.get("swap_s") or 0)
            enc = float(ref_stages.get("encode_s") or 0)
            # swap и restore идут параллельно на разных GPU — не вычитаем restore из swap.
            timings[gen_key] = max(0.0, ss)
            if rs > 0:
                timings["face_restore"] = rs
            if enc > 0:
                timings["encode"] = enc
            for dup in ("swap_s", "restore_s", "encode_s", "total_s"):
                timings.pop(dup, None)
            job.stage_timings = dict(timings)

        if (
            mode in {"ref_video", "refvideo", "faceswap"}
            and settings.ref_video_face_restore
        ):
            inline_done = bool(getattr(generator, "last_inline_restored", False))
            if inline_done and "face_restore" not in timings:
                rsec = getattr(generator, "last_restore_sec", None)
                if rsec is not None:
                    timings["face_restore"] = float(rsec)
                    timings[gen_key] = max(0.0, float(gen_sec) - float(rsec))
                    job.stage_timings = dict(timings)
                logger.info(
                    "face_restore: инлайн в swap-цикле (%.1f с) — 2-й проход пропущен",
                    float(rsec or 0.0),
                )
            elif inline_done:
                logger.info(
                    "face_restore: инлайн в swap-цикле (%.1f с) — 2-й проход пропущен",
                    float(timings.get("face_restore") or 0),
                )
            else:
                from app.face_restore import is_available, restore_video_faces

                if is_available():
                    job.message = "Улучшаем чёткость лица…"
                    t0 = time.perf_counter()
                    try:
                        restore_video_faces(output)
                        _stage_done(job, timings, "face_restore", t0)
                    except Exception as exc:
                        logger.warning("GFPGAN пропущен (ролик без restore): %s", exc)
                else:
                    logger.warning(
                        "REF_VIDEO_FACE_RESTORE=true, но GFPGAN не установлен — пропуск"
                    )

        ref_minimal = (
            mode in {"ref_video", "refvideo", "faceswap"}
            and settings.ref_video_skip_festival_fx
        ) or mode in PORTRAIT_MODES

        use_atmosphere = settings.festival_atmosphere and not ref_minimal
        if mode == "liveportrait" and not settings.liveportrait_festival_atmosphere:
            use_atmosphere = False
        if use_atmosphere:
            job.message = "Добавляем фестивальные огни и блики…"
            t0 = time.perf_counter()
            apply_festival_atmosphere(output, float(settings.video_fps))
            _stage_done(job, timings, "atmosphere", t0)

        overlay_path = settings.brand_overlay_path
        use_frame = settings.festival_frame and not ref_minimal
        if use_frame:
            job.message = "Накладываем фирменную рамку…"
            overlay_path = ensure_festival_frame_asset(
                settings.video_width, settings.video_height
            )
        if overlay_path and Path(overlay_path).exists():
            t0 = time.perf_counter()
            apply_overlay(output, overlay_path)
            _stage_done(job, timings, "overlay", t0)

        music = settings.background_music_path
        if music and Path(music).exists():
            job.message = "Подмешиваем музыку…"
            t0 = time.perf_counter()
            mux_audio(output, settings.background_music_path)
            _stage_done(job, timings, "music", t0)

        from app.output_dispatch import (
            dispatch_job_output,
            should_print_file,
            should_upload_file,
        )
        from app.qr_util import build_download_url, save_job_qr

        public_url: str | None = None
        if should_upload_file() or should_print_file(output):
            job.message = "Отправляем фото на сервер…"
            qr_target = build_download_url(out_name)
            dispatch = dispatch_job_output(
                output,
                job_id,
                guest_profile=guest_profile,
                download_url=qr_target,
                output_filename=out_name,
            )
            if dispatch.upload_sec is not None:
                timings["upload"] = dispatch.upload_sec
            if dispatch.print_sec is not None:
                timings["print"] = dispatch.print_sec
            job.upload_ok = dispatch.upload_ok
            job.upload_error = dispatch.upload_error
            job.print_ok = dispatch.print_ok
            job.print_error = dispatch.print_error
            public_url = dispatch.public_url
            if not settings.output_dispatch_fail_open and (
                dispatch.upload_ok is False or dispatch.print_ok is False
            ):
                raise RuntimeError(dispatch.summary_ru() or "Ошибка отправки/печати")

        job.message = "Готовим QR…"
        t0 = time.perf_counter()
        save_job_qr(
            job_id,
            out_name,
            download_url=public_url or build_download_url(out_name),
        )
        _stage_done(job, timings, "qr", t0)

        if guest_profile is not None and mode in {"ref_video", "refvideo", "faceswap"}:
            from app.driving_catalog import pick_driving_video

            try:
                job.driving_video = pick_driving_video(guest_profile).name
            except Exception:
                pass

        job.status = JobStatus.DONE
        job.output_filename = out_name
        job.total_sec = time.perf_counter() - t_job
        job.generation_sec = gen_sec
        job.stage_timings = timings
        stages_ru = {
            "guest_profile": "профиль",
            "face_swap": "face swap",
            "portrait": "InstantID",
            "generation": "генерация",
            "face_restore": "GFPGAN",
            "atmosphere": "атмосфера",
            "overlay": "рамка",
            "music": "музыка",
            "qr": "QR",
            "upload": "сервер",
            "print": "печать",
        }
        parts = [
            f"{stages_ru.get(k, k)} {v:.1f}с"
            for k, v in timings.items()
            if isinstance(v, (int, float))
        ]
        timing_hint = f" ({', '.join(parts)}, всего {job.total_sec:.1f}с)" if parts else ""
        is_portrait = out_ext in {".jpg", ".jpeg", ".png", ".webp"}
        if job.print_ok:
            done_hint = (
                "Готово! Заберите фото с принтера"
                if is_portrait
                else "Готово! Заберите распечатку с принтера"
            )
        elif is_portrait:
            done_hint = "Готово! Сканируйте QR и забирайте портрет"
        else:
            done_hint = "Готово! Сканируйте QR и забирайте ролик"
        job.message = f"{done_hint}{timing_hint}"
        logger.info(
            "job %s done in %.2f с, этапы: %s",
            job_id,
            job.total_sec,
            ", ".join(
                f"{k}={v:.2f}s" for k, v in timings.items() if isinstance(v, (int, float))
            ),
        )
    except Exception as exc:
        job.status = JobStatus.ERROR
        job.message = str(exc)
    finally:
        shutil.rmtree(job_path, ignore_errors=True)
