import base64
from pathlib import Path

import app.cuda_bootstrap  # noqa: F401 — cuDNN PATH до onnxruntime

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.pipeline import JobStatus, PORTRAIT_MODES, create_job_from_upload, get_job, process_job
from app.qr_util import build_download_url, qr_output_path, save_job_qr
from app.upload_queue import start_upload_queue_worker

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
ASSETS_DIR = ROOT / "assets"

app = FastAPI(title="GIGAvibe Kiosk", version="0.2.0")

if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


@app.on_event("startup")
def startup() -> None:
    start_upload_queue_worker()
    mode = settings.generator_mode.lower()
    if mode in {"ref_video", "refvideo", "faceswap"}:
        from app.generators.ref_video import RefVideoGenerator

        if not RefVideoGenerator.is_available():
            print(
                "[GIGAvibe] WARN: ref_video недоступен (insightface/onnx или models/). "
                "Перезапустите через .\\run.ps1",
                flush=True,
            )
            return
        engine = (settings.ref_video_swap_engine or "inswapper").strip().lower()
        if engine in {"", "inswapper"}:
            print(
                "[GIGAvibe] WARN: REF_VIDEO_SWAP_ENGINE=inswapper — квадратная маска и "
                "медленный paste. Рекомендуется inswapper_fast (см. .env.example).",
                flush=True,
            )
        try:
            RefVideoGenerator._load_models()
            prov = RefVideoGenerator.last_onnx_provider or "?"
            swap_dev = settings.ref_video_swap_device_id
            print(
                f"[GIGAvibe] ref_video engine={engine}, swap cuda:{swap_dev}, ONNX: {prov}",
                flush=True,
            )
            pipeline = (settings.ref_video_pipeline or "legacy").strip().lower()
            restore_eng = (settings.ref_video_restore_engine or "facexlib").strip().lower()
            print(
                f"[GIGAvibe] ref_video pipeline={pipeline}, restore_engine={restore_eng}",
                flush=True,
            )
            if (
                pipeline == "rope_v1"
                and restore_eng == "onnx_512"
                and settings.ref_video_face_restore
            ):
                try:
                    RefVideoGenerator._load_gfpgan_onnx()
                    sdev = settings.ref_video_swap_device_id
                    print(
                        f"[GIGAvibe] GFPGAN ONNX inline resident on cuda:{sdev} (full-GPU)",
                        flush=True,
                    )
                    if settings.ref_video_face_parser:
                        RefVideoGenerator._load_face_parser()
                        print(
                            f"[GIGAvibe] face parser resident on cuda:{sdev}",
                            flush=True,
                        )
                    devs = RefVideoGenerator._parse_gpu_devices()
                    if len(devs) > 1:
                        for _d in devs:
                            RefVideoGenerator._build_worker(_d)
                        print(
                            f"[GIGAvibe] data-parallel workers resident on GPUs {devs}",
                            flush=True,
                        )
                    print("[GIGAvibe] warming up full-GPU pipeline…", flush=True)
                    RefVideoGenerator.warmup_pipeline()
                    print("[GIGAvibe] warmup complete (kernels compiled)", flush=True)
                except Exception as exc:
                    print(f"[GIGAvibe] WARN: GFPGAN ONNX warmup: {exc}", flush=True)
            elif settings.ref_video_face_restore:
                from app.face_restore import is_available, warmup_model

                if is_available():
                    warmup_model()
                    rdev = settings.ref_video_restore_device_id
                    print(
                        f"[GIGAvibe] GFPGAN facexlib resident on cuda:{rdev}",
                        flush=True,
                    )
                else:
                    print("[GIGAvibe] WARN: GFPGAN facexlib model missing", flush=True)
        except Exception as exc:
            print(f"[GIGAvibe] WARN: ref_video warmup failed: {exc}", flush=True)
        return

    if mode in {"nanobanana", "nano_banana", "festival_nanobanana", "nana_banana"}:
        from app.generators.festival_nanobanana import FestivalNanobananaGenerator

        if FestivalNanobananaGenerator.is_available():
            backend = FestivalNanobananaGenerator.backend()
            if backend == "proxy":
                print(
                    f"[GIGAvibe] nanobanana: proxy nanobananaapi.ai, version={settings.nanobanana_api_version} "
                    f"(style={settings.nanobanana_style}, {settings.nanobanana_aspect_ratio})",
                    flush=True,
                )
            elif backend == "aitunnel":
                print(
                    f"[GIGAvibe] nanobanana: AITunnel, model={settings.nanobanana_model} "
                    f"(style={settings.nanobanana_style}, {settings.nanobanana_aspect_ratio})",
                    flush=True,
                )
            elif backend == "quatarly":
                print(
                    f"[GIGAvibe] nanobanana: Quatarly, model={settings.nanobanana_model} "
                    f"(style={settings.nanobanana_style}, {settings.nanobanana_aspect_ratio})",
                    flush=True,
                )
            else:
                print(
                    f"[GIGAvibe] nanobanana: Gemini direct, model={settings.nanobanana_model} "
                    f"(style={settings.nanobanana_style}, {settings.nanobanana_aspect_ratio})",
                    flush=True,
                )
        else:
            print(
                "[GIGAvibe] WARN: nanobanana недоступен — AITUNNEL_API_KEY (backend=aitunnel), "
                "QUATARLY_API_KEY (backend=quatarly), "
                "GEMINI_API_KEY (backend=gemini) или NANOBANANA_API_KEY (backend=proxy)",
                flush=True,
            )
        return

    if mode in {"festival_portrait", "portrait", "portrait_still"}:
        from app.generators.festival_portrait import FestivalPortraitGenerator

        if not FestivalPortraitGenerator.is_available():
            print(
                "[GIGAvibe] WARN: festival_portrait недоступен (SDXL/InstantID). "
                "См. scripts/test_festival_portrait.py",
                flush=True,
            )
            return
        try:
            from app.generators.keyframe_instantid import warmup_model

            warmup_model()
            dev = settings.instantid_device_id
            print(
                f"[GIGAvibe] festival_portrait: InstantID+SDXL resident on cuda:{dev}",
                flush=True,
            )
        except Exception as exc:
            print(f"[GIGAvibe] WARN: festival_portrait warmup failed: {exc}", flush=True)
        return

    if not settings.preload_model_on_startup:
        return
    if mode == "liveportrait":
        from app.generators.liveportrait import LivePortraitGenerator, warmup_model as warmup_lp

        if LivePortraitGenerator.is_available():
            warmup_lp()
        return

    if mode not in {"svd", "ltx", "auto"}:
        return

    if mode in {"ltx", "auto"}:
        from app.generators.ltx import LtxGenerator, warmup_model as warmup_ltx

        if LtxGenerator.is_available():
            # Резидентный InstantID на cuda:1: греем заранее, чтобы первый гость не ждал ~1.5 мин.
            if (settings.keyframe_mode or "").strip().lower() == "instantid" and settings.keyframe_keep_resident:
                try:
                    from app.generators.keyframe_instantid import warmup_model as warmup_kf

                    warmup_kf()
                    print("[GIGAvibe] InstantID keyframe ready (resident)", flush=True)
                except Exception as exc:
                    print(f"[GIGAvibe] WARN: InstantID warmup failed: {exc}", flush=True)
            warmup_ltx()
            return

    from app.generators.svd import SvdGenerator, warmup_model as warmup_svd

    if mode in {"svd", "auto"} and SvdGenerator.is_available():
        warmup_svd()


def _static_cache_token() -> str:
    """Версия статики по mtime — сбрасывает кэш киоска после деплоя."""
    parts: list[str] = []
    for name in ("app.js", "style.css", "css/figma-fonts.css"):
        try:
            parts.append(str(int((WEB_DIR / name).stat().st_mtime)))
        except OSError:
            parts.append("0")
    return "-".join(parts)


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    v = _static_cache_token()
    html = html.replace(
        'href="/static/css/figma-fonts.css"',
        f'href="/static/css/figma-fonts.css?v={v}"',
    )
    html = html.replace('href="/static/style.css"', f'href="/static/style.css?v={v}"')
    html = html.replace('src="/static/app.js"', f'src="/static/app.js?v={v}"')
    return HTMLResponse(
        html,
        headers={"Cache-Control": "no-cache, must-revalidate"},
    )


@app.post("/api/jobs")
async def create_job(
    background_tasks: BackgroundTasks,
    photo: UploadFile = File(...),
) -> dict:
    data = await photo.read()
    if len(data) < 1024:
        raise HTTPException(400, "Слишком маленький файл")
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(400, "Файл больше 15 МБ")

    job_id = create_job_from_upload(data, photo.filename or "photo.jpg")
    background_tasks.add_task(process_job, job_id)
    return {"job_id": job_id}


def _qr_data_url(job_id: str) -> str | None:
    path = qr_output_path(job_id)
    if not path.exists():
        return None
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> dict:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(404, "Задача не найдена")

    payload = {
        "job_id": job.id,
        "status": job.status.value,
        "message": job.message,
    }
    if job.guest_gender:
        payload["guest_gender"] = job.guest_gender
    if job.guest_build:
        payload["guest_build"] = job.guest_build
    if job.guest_age_group:
        payload["guest_age_group"] = job.guest_age_group
    if job.guest_age_years is not None:
        payload["guest_age_years"] = job.guest_age_years
    if job.driving_video:
        payload["driving_video"] = job.driving_video
    if job.stage_timings:
        timings_out: dict[str, float | str] = {}
        numeric_sum = 0.0
        for k, v in job.stage_timings.items():
            if isinstance(v, (int, float)):
                fv = round(float(v), 1)
                timings_out[k] = fv
                numeric_sum += fv
            else:
                timings_out[k] = str(v)
        payload["stage_timings"] = timings_out
        if job.status == JobStatus.PROCESSING and numeric_sum > 0:
            payload["elapsed_sec"] = round(numeric_sum, 1)
    if job.total_sec is not None:
        payload["total_sec"] = round(job.total_sec, 1)

    if job.status == JobStatus.DONE and job.output_filename:
        ext = Path(job.output_filename).suffix.lower()
        is_image = ext in {".png", ".jpg", ".jpeg", ".webp"}
        media_path = f"/outputs/{job.output_filename}"
        payload["download_url"] = build_download_url(job.output_filename)
        payload["output_kind"] = "image" if is_image else "video"
        if is_image:
            payload["image_path"] = media_path
        else:
            payload["video_path"] = media_path
        payload["qr_path"] = f"/api/jobs/{job_id}/qr.png"
        qr_inline = _qr_data_url(job_id)
        if qr_inline:
            payload["qr_data_url"] = qr_inline
        if job.generation_sec is not None:
            payload["generation_sec"] = round(job.generation_sec, 1)
        if job.upload_ok is not None:
            payload["upload_ok"] = job.upload_ok
        if job.upload_error:
            payload["upload_error"] = job.upload_error
        if job.print_ok is not None:
            payload["print_ok"] = job.print_ok
        if job.print_error:
            payload["print_error"] = job.print_error
    return payload


@app.post("/api/jobs/{job_id}/dispatch")
def redispatch_job(job_id: str) -> dict:
    """Повторная отправка на сервер / печать для готового job."""
    from app.output_dispatch import dispatch_job_output, dispatch_status_dict

    job = get_job(job_id)
    if job is None:
        raise HTTPException(404, "Задача не найдена")
    if job.status != JobStatus.DONE or not job.output_filename:
        raise HTTPException(409, "Задача ещё не готова")

    output = settings.data_dir / "outputs" / job.output_filename
    if not output.exists():
        raise HTTPException(404, "Файл результата не найден")

    download_url = build_download_url(job.output_filename)
    result = dispatch_job_output(
        output,
        job_id,
        download_url=download_url,
        output_filename=job.output_filename,
    )
    job.upload_ok = result.upload_ok
    job.upload_error = result.upload_error
    job.print_ok = result.print_ok
    job.print_error = result.print_error
    if result.summary_ru():
        job.message = result.summary_ru()
    return {"job_id": job_id, **dispatch_status_dict(result)}


@app.get("/api/jobs/{job_id}/qr.png")
def job_qr(job_id: str) -> FileResponse:
    job = get_job(job_id)
    if job is None or job.status != JobStatus.DONE or not job.output_filename:
        raise HTTPException(404, "Задача ещё не готова")

    path = qr_output_path(job_id)
    if not path.exists():
        save_job_qr(job_id, job.output_filename)
    if not path.exists():
        raise HTTPException(500, "Не удалось создать QR")

    return FileResponse(
        path,
        media_type="image/png",
        filename=f"gigavibe-{job_id}.png",
    )


@app.get("/outputs/{filename}")
def download_output(filename: str) -> FileResponse:
    path = settings.data_dir / "outputs" / filename
    if not path.exists():
        raise HTTPException(404)
    ext = path.suffix.lower()
    if ext == ".mp4":
        return FileResponse(
            path,
            media_type="video/mp4",
            filename=filename,
            headers={"Accept-Ranges": "bytes"},
        )
    if ext in {".png", ".jpg", ".jpeg", ".webp"}:
        media = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }[ext]
        return FileResponse(path, media_type=media, filename=filename)
    raise HTTPException(404)


@app.get("/api/config")
def kiosk_config() -> dict:
    mode = settings.generator_mode.lower()
    output_kind = "image" if mode in PORTRAIT_MODES or mode == "auto" else "video"
    return {
        "generator_mode": settings.generator_mode,
        "output_kind": output_kind,
        "video_width": settings.video_width,
        "video_height": settings.video_height,
        "video_fps": settings.video_fps,
        "video_duration_sec": settings.video_duration_sec,
        "kiosk_auto_camera": settings.kiosk_auto_camera,
        "kiosk_smile_capture": settings.kiosk_smile_capture,
        "kiosk_smile_threshold": settings.kiosk_smile_threshold,
        "kiosk_smile_hold_frames": settings.kiosk_smile_hold_frames,
        "kiosk_smile_hold_ms": settings.kiosk_smile_hold_ms,
        "kiosk_smile_detect_stride": settings.kiosk_smile_detect_stride,
        "kiosk_smile_cooldown_ms": settings.kiosk_smile_cooldown_ms,
        "kiosk_face_min_size": settings.kiosk_face_min_size,
        "kiosk_face_hold_frames": settings.kiosk_face_hold_frames,
        "kiosk_face_release_frames": settings.kiosk_face_release_frames,
        "kiosk_face_hold_ms": settings.kiosk_face_hold_ms,
        "kiosk_face_release_ms": settings.kiosk_face_release_ms,
        "kiosk_face_detect_stride": settings.kiosk_face_detect_stride,
        "kiosk_jpeg_quality": settings.kiosk_jpeg_quality,
        "kiosk_test_mode": settings.kiosk_test_mode,
        "output_upload_enabled": settings.output_upload_enabled,
        "print_enabled": settings.print_enabled,
    }


@app.get("/api/health")
def health() -> dict:
    from app.generators.factory import get_generator
    from app.generators.liveportrait import LivePortraitGenerator
    from app.generators.ltx import LtxGenerator
    from app.generators.ref_video import RefVideoGenerator
    from app.generators.svd import SvdGenerator

    gen_name: str | None = None
    gen_error: str | None = None
    ref_prov = RefVideoGenerator.last_onnx_provider
    try:
        gen = get_generator()
        gen_name = gen.__class__.__name__
        if isinstance(gen, RefVideoGenerator):
            ref_prov = RefVideoGenerator.last_onnx_provider
    except RuntimeError as exc:
        gen_error = str(exc)

    warnings: list[str] = []
    mode = settings.generator_mode.lower()
    engine = (settings.ref_video_swap_engine or "").strip().lower()
    if mode in {"ref_video", "refvideo", "faceswap"}:
        if engine in {"", "inswapper"}:
            warnings.append(
                "REF_VIDEO_SWAP_ENGINE=inswapper: прямоугольная маска InsightFace "
                "и медленный CPU-paste. Укажите inswapper_fast."
            )
        elif engine == "inswapper_fast" and ref_prov == "CPUExecutionProvider":
            warnings.append(
                "ONNX на CPU: swap будет в разы медленнее. Запускайте через .\\run.ps1 "
                "и проверьте CUDAExecutionProvider."
            )

    return {
        "ok": gen_error is None,
        "generator_mode": settings.generator_mode,
        "active_generator": gen_name,
        "generator_error": gen_error,
        "warnings": warnings,
        "ref_video_onnx_provider": ref_prov,
        "ref_video_swap_engine": settings.ref_video_swap_engine,
        "ref_video_swap_device_id": settings.ref_video_swap_device_id,
        "ref_video_restore_device_id": settings.ref_video_restore_device_id,
        "ref_video_face_restore": settings.ref_video_face_restore,
        "ref_video_restore_every_n": settings.ref_video_restore_every_n,
        "ref_video_restore_interpolate": settings.ref_video_restore_interpolate,
        "ref_video_inline_restore": settings.ref_video_inline_restore,
        "ref_video_inline_restore_weight": settings.ref_video_inline_restore_weight,
        "ref_video_restore_workers": settings.ref_video_restore_workers,
        "ref_video_restore_fp16": settings.ref_video_restore_fp16,
        "ref_video_det_size": settings.ref_video_det_size,
        "ref_video_gpu_paste": settings.ref_video_gpu_paste,
        "ref_video_pipeline": settings.ref_video_pipeline,
        "ref_video_diff_amount": settings.ref_video_diff_amount,
        "ref_video_restore_engine": settings.ref_video_restore_engine,
        "ref_video_gfpgan_onnx_path": str(settings.ref_video_gfpgan_onnx_path),
        "ref_video_gfpgan_onnx_available": (
            __import__("app.generators.gfpgan_onnx", fromlist=["is_available"]).is_available(
                Path(settings.ref_video_gfpgan_onnx_path)
            )
        ),
        "ref_video_stage_timings": RefVideoGenerator.last_stage_timings,
        "ref_video_serialize_jobs": settings.ref_video_serialize_jobs,
        "ref_video_swap_workers": settings.ref_video_swap_workers,
        "ref_video_last_restore_strategy": RefVideoGenerator.last_restore_strategy,
        "ref_video_lean_detect": settings.ref_video_lean_detect,
        "ref_video_threaded_read": settings.ref_video_threaded_read,
        "ref_video_read_queue": settings.ref_video_read_queue,
        "inswapper_fast_model_path": str(settings.inswapper_fast_model_path),
        "cuda_available": LtxGenerator.is_available(),
        "liveportrait_available": LivePortraitGenerator.is_available(),
        "ref_video_available": RefVideoGenerator.is_available(),
        "festival_portrait_available": __import__(
            "app.generators.festival_portrait",
            fromlist=["FestivalPortraitGenerator"],
        ).FestivalPortraitGenerator.is_available(),
        "nanobanana_available": __import__(
            "app.generators.festival_nanobanana",
            fromlist=["FestivalNanobananaGenerator"],
        ).FestivalNanobananaGenerator.is_available(),
        "nanobanana_backend": settings.nanobanana_backend,
        "nanobanana_model": settings.nanobanana_model,
        "instantid_device_id": settings.instantid_device_id,
        "ltx_model": settings.ltx_model_id,
        "public_base_url": settings.effective_public_base_url(),
        "video_width": settings.video_width,
        "video_height": settings.video_height,
        "output_upload_enabled": settings.output_upload_enabled,
        "output_upload_url": settings.output_upload_url,
        "qr_public_base_url": settings.qr_public_base_url or None,
        "print_enabled": settings.print_enabled,
        "print_printer_name": settings.print_printer_name,
    }


def run() -> None:
    import uvicorn

    ssl_kwargs: dict = {}
    if settings.use_https and settings.ssl_certfile and settings.ssl_keyfile:
        cert = Path(settings.ssl_certfile)
        key = Path(settings.ssl_keyfile)
        if cert.exists() and key.exists():
            ssl_kwargs = {
                "ssl_certfile": str(cert),
                "ssl_keyfile": str(key),
            }
            print(f"[GIGAvibe] HTTPS enabled: {cert.name}", flush=True)
        else:
            print(
                f"[GIGAvibe] WARN: use_https=true, но сертификат не найден "
                f"({cert} / {key}). Запуск по HTTP.",
                flush=True,
            )

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        **ssl_kwargs,
    )


if __name__ == "__main__":
    run()
