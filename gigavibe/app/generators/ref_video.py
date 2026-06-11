"""
Референс-ролик как визуальная база + лицо гостя (InsightFace inswapper).
Каждый кадр — из MP4; подменяется только лицо (нужен полный buffalo_l с w600k_r50).
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from app.generators.base import VideoGenerator
from app.generators.liveportrait import _ffmpeg_exe

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent.parent
# Полный buffalo_l (с recognition). НЕ vendor/.../insightface — там только det без embedding.
INSIGHTFACE_ROOT = ROOT / "models" / "insightface"
INSWAPPER_URL = (
    "https://huggingface.co/ezioruan/inswapper_128.onnx/resolve/main/inswapper_128.onnx"
)


def _abs_path(raw) -> Path:
    """Абсолютный путь: относительный считается от корня проекта."""
    p = Path(raw)
    if not p.is_absolute():
        p = ROOT / p
    return p


def _swapper_path() -> Path:
    """Путь к весам face-swap из настроек (по умолчанию inswapper_128).
    Относительный путь считается от корня проекта."""
    from app.config import settings

    return _abs_path(settings.ref_video_swapper_path)


def _pick_reference_mp4(profile=None) -> Path:
    from app.config import settings

    if profile is not None:
        from app.driving_catalog import pick_driving_video

        return pick_driving_video(profile)

    if settings.liveportrait_driving_path:
        p = Path(settings.liveportrait_driving_path)
        if not p.is_absolute():
            p = ROOT / p
        if p.suffix.lower() == ".pkl":
            for alt in (p.with_suffix(".MP4"), p.with_suffix(".mp4")):
                if alt.exists():
                    return alt
        if p.exists() and p.suffix.lower() in {".mp4", ".mov", ".avi"}:
            return p
        raise FileNotFoundError(f"Референс-видео не найдено: {p}")

    d = ROOT / "assets" / "driving"
    for ext in ("*.MP4", "*.mp4"):
        files = sorted(d.glob(ext))
        if files:
            return files[0]
    raise FileNotFoundError("Положите референс .mp4 в assets/driving/")


def _ensure_inswapper() -> Path:
    path = _swapper_path()
    if path.exists() and path.stat().st_size > 1_000_000:
        return path
    # Автоскачиваем только дефолтный inswapper_128. Кастомный путь (напр. 512)
    # пользователь кладёт сам — молча его не качаем (другого официального источника нет).
    if path.name != "inswapper_128.onnx":
        raise FileNotFoundError(
            f"Файл face-swap не найден: {path}. Положите модель по этому пути "
            "или измените REF_VIDEO_SWAPPER_PATH в .env"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    import urllib.request

    urllib.request.urlretrieve(INSWAPPER_URL, path)
    return path


def _ensure_buffalo_l() -> None:
    marker = INSIGHTFACE_ROOT / "models" / "buffalo_l" / "w600k_r50.onnx"
    if marker.exists():
        return
    from insightface.app import FaceAnalysis

    INSIGHTFACE_ROOT.mkdir(parents=True, exist_ok=True)
    app = FaceAnalysis(name="buffalo_l", root=str(INSIGHTFACE_ROOT))
    app.prepare(ctx_id=-1, det_size=(640, 640))


def _largest_face(faces: list):
    if not faces:
        return None
    return max(
        faces,
        key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
    )


def _trim_reference_mp4(src: Path, tmp: Path, duration_sec: float) -> Path:
    """Ровно первые N секунд референса (без сжатия всего ролика в 5 с)."""
    if duration_sec <= 0:
        return src
    ffmpeg = _ffmpeg_exe()
    if not ffmpeg:
        return src
    out = tmp / f"{src.stem}_first{duration_sec:.1f}s.mp4"
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(src.resolve()),
        "-t",
        f"{duration_sec:.3f}",
        "-an",
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0 and out.exists() and out.stat().st_size > 5000:
        return out
    logger.warning("ffmpeg trim failed, using full reference: %s", (r.stderr or "")[-500:])
    return src


def _ensure_onnx_cuda_dlls() -> None:
    from app.cuda_bootstrap import ensure_onnx_cuda

    ensure_onnx_cuda()


def _onnx_providers(device_id: int = 0) -> list:
    _ensure_onnx_cuda_dlls()
    import onnxruntime as ort

    avail = set(ort.get_available_providers())
    if "CUDAExecutionProvider" in avail:
        return [
            ("CUDAExecutionProvider", {"device_id": int(device_id)}),
            "CPUExecutionProvider",
        ]
    return ["CPUExecutionProvider"]


def _probe_active_provider(providers: list) -> str:
    """Реальный провайдер первой сессии (не только список «доступных»)."""
    import onnxruntime as ort

    det = INSIGHTFACE_ROOT / "models" / "buffalo_l" / "det_10g.onnx"
    first = providers[0]
    fallback = first[0] if isinstance(first, tuple) else str(first)
    if not det.exists():
        return fallback
    try:
        sess = ort.InferenceSession(str(det), providers=providers)
        return sess.get_providers()[0]
    except Exception:
        return fallback


class RefVideoGenerator(VideoGenerator):
    _face_app = None
    _swapper = None
    _simswap = None
    _inswapper_fast = None
    _gfpgan_onnx = None
    _face_parser = None
    _workers: dict = {}  # dev_id -> (face_app, fast_engine, gfpgan_engine, parser)
    last_generation_sec: float | None = None
    last_onnx_provider: str | None = None
    # Инлайн-restore: выставляется в generate(), читается pipeline.py.
    last_inline_restored: bool = False  # restore сделан внутри swap-цикла
    last_restore_sec: float | None = None  # wall-clock время restore-пула
    last_restore_strategy: str | None = None
    last_stage_timings: dict[str, float] | None = None  # swap_s, restore_s, encode_s, …

    @classmethod
    def is_available(cls) -> bool:
        try:
            import insightface  # noqa: F401
            import onnxruntime  # noqa: F401

            _ensure_buffalo_l()
            return (INSIGHTFACE_ROOT / "models" / "buffalo_l" / "w600k_r50.onnx").exists()
        except Exception:
            return False

    @classmethod
    def _load_models(cls):
        if cls._face_app is not None and cls._swapper is not None:
            return cls._face_app, cls._swapper

        import insightface
        from insightface.app import FaceAnalysis

        from app.config import settings

        _ensure_buffalo_l()
        _ensure_inswapper()
        dev_id = int(settings.ref_video_swap_device_id)
        providers = _onnx_providers(dev_id)
        first = providers[0]
        uses_cuda = first == "CUDAExecutionProvider" or (
            isinstance(first, tuple) and first[0] == "CUDAExecutionProvider"
        )
        ctx = dev_id if uses_cuda else -1

        cls._face_app = FaceAnalysis(
            name="buffalo_l",
            root=str(INSIGHTFACE_ROOT),
            providers=providers,
        )
        cls._face_app.prepare(ctx_id=ctx, det_size=(640, 640), det_thresh=0.4)
        engine = (settings.ref_video_swap_engine or "inswapper").strip().lower()
        if engine == "simswap":
            from app.generators.simswap import SimSwapEngine

            sm = SimSwapEngine(
                model_path=_abs_path(settings.simswap_model_path),
                arcface_path=_abs_path(settings.simswap_arcface_path),
                providers=providers,
            )
            sm.input_mean = float(settings.simswap_input_mean)
            sm.input_std = float(settings.simswap_input_std)
            cls._simswap = sm
            # InsightFace inswapper не грузим — экономим VRAM.
            cls._swapper = sm
            logger.info("ref_video: swap engine = SimSwap 512 (%s)", sm.model_path.name)
        elif engine == "inswapper_fast":
            from app.generators.inswapper import InswapperEngine

            fe = InswapperEngine(
                model_path=_abs_path(settings.inswapper_fast_model_path),
                providers=providers,
                device_id=dev_id,
                emap_source_path=_swapper_path(),  # fp32 inswapper как источник emap
            )
            cls._inswapper_fast = fe
            cls._swapper = fe
            pipeline = (settings.ref_video_pipeline or "legacy").strip().lower()
            logger.info(
                "ref_video: swap engine = inswapper_fast (%s), pipeline=%s, gpu_pipeline=%s",
                fe.model_path.name,
                pipeline,
                fe.gpu_pipeline,
            )
        else:
            swapper_path = _swapper_path()
            cls._swapper = insightface.model_zoo.get_model(
                str(swapper_path),
                providers=providers,
            )
            logger.info("ref_video: swap engine = inswapper (%s)", swapper_path.name)
        active = _probe_active_provider(providers)
        cls.last_onnx_provider = active
        logger.info(
            "ref_video: inswapper+buffalo_l resident on cuda:%s, ONNX active %s",
            dev_id,
            active,
        )
        return cls._face_app, cls._swapper

    @classmethod
    def _load_gfpgan_onnx(cls):
        if cls._gfpgan_onnx is not None:
            return cls._gfpgan_onnx
        from app.config import settings
        from app.generators.gfpgan_onnx import GfpganOnnxEngine, is_available

        path = _abs_path(settings.ref_video_gfpgan_onnx_path)
        if not is_available(path):
            return None
        # Inline GPU-режим: GFPGAN на той же карте, что swap (кадр уже на GPU0,
        # без cross-GPU PCIe-копий в середине конвейера).
        dev = int(settings.ref_video_swap_device_id)
        cls._gfpgan_onnx = GfpganOnnxEngine(
            model_path=path,
            providers=_onnx_providers(dev),
            device_id=dev,
        )
        logger.info("ref_video: GFPGAN ONNX inline on cuda:%s (%s)", dev, path.name)
        return cls._gfpgan_onnx

    @classmethod
    def warmup_pipeline(cls) -> None:
        """Прогрев full-GPU конвейера на синтетическом кадре: компилирует CUDA/cuDNN
        ядра (detect+swap+GFPGAN+parser+paste) на каждой карте при старте, чтобы
        первый реальный ролик не был «холодным» (~30 с автотюнинга)."""
        from app.config import settings

        pipeline = (settings.ref_video_pipeline or "legacy").strip().lower()
        restore_engine = (settings.ref_video_restore_engine or "facexlib").strip().lower()
        if not (
            pipeline == "rope_v1"
            and restore_engine == "onnx_512"
            and bool(settings.ref_video_face_restore)
        ):
            return
        try:
            cls._load_models()
            fast = cls._inswapper_fast
            if fast is None:
                return
            devices = cls._parse_gpu_devices() or [int(settings.ref_video_swap_device_id)]

            # Синтетический кадр + стандартные arcface-точки лица в центре кадра.
            h, w = int(settings.video_height), int(settings.video_width)
            frame = np.full((h, w, 3), 96, dtype=np.uint8)
            arcface_dst = np.array(
                [
                    [38.2946, 51.6963],
                    [73.5318, 51.5014],
                    [56.0252, 71.7366],
                    [41.5493, 92.3655],
                    [70.7299, 92.2041],
                ],
                dtype=np.float32,
            )
            face_px = 256.0
            kps = arcface_dst / 112.0 * face_px
            kps[:, 0] += (w - face_px) / 2.0
            kps[:, 1] += (h - face_px) / 2.0
            kps = kps.astype(np.float32)

            rng = np.random.default_rng(0)
            emb = rng.standard_normal(512).astype(np.float32)
            emb /= (np.linalg.norm(emb) + 1e-9)
            latent = fast.embed_latent(emb)
            restore_weight = float(settings.ref_video_inline_restore_weight)
            det_sz = max(int(settings.ref_video_det_size), 320)

            for d in devices:
                fa, fe, ge, pe = cls._build_worker(d)
                for _ in range(2):  # 2 прогона: cuDNN autotune стабилизируется
                    try:
                        fa.det_model.detect(
                            frame, max_num=0, metric="default",
                            input_size=(det_sz, det_sz),
                        )
                    except Exception:
                        pass
                    try:
                        fe.swap(
                            frame, kps, latent,
                            gfpgan=ge, restore_weight=restore_weight, parser=pe,
                        )
                    except Exception as exc:
                        logger.warning("warmup swap fail (cuda:%s): %s", d, exc)
                logger.info("ref_video: warmup done on cuda:%s", d)
        except Exception as exc:
            logger.warning("ref_video warmup_pipeline skip: %s", exc)

    @classmethod
    def _load_face_parser(cls):
        from app.config import settings

        if not bool(settings.ref_video_face_parser):
            return None
        if cls._face_parser is not None:
            return cls._face_parser
        from app.generators.face_parser_onnx import FaceParserEngine, is_available

        path = _abs_path(settings.ref_video_parser_path)
        if not is_available(path):
            logger.warning("face parser: модель недоступна (%s) — без масок", path)
            return None
        dev = int(settings.ref_video_swap_device_id)
        cls._face_parser = FaceParserEngine(
            model_path=path, providers=_onnx_providers(dev), device_id=dev
        )
        logger.info("ref_video: face parser on cuda:%s (%s)", dev, path.name)
        return cls._face_parser

    def _run_data_parallel(
        self,
        devices: list[int],
        frame_iter,
        fast_latent,
        restore_weight: float,
        lean: bool,
        det_size,
        read_queue: int,
    ):
        """Data-parallel full-GPU: кадры делятся между картами, каждая делает
        detect+swap+GFPGAN+paste своим комплектом. Возврат (raw_frames, swapped, no_face)."""
        import queue as _q
        import threading as _th

        workers = [type(self)._build_worker(d) for d in devices]
        in_q: _q.Queue = _q.Queue(maxsize=max(2 * len(devices), int(read_queue)))
        sentinel = object()
        results: dict[int, np.ndarray] = {}
        lock = _th.Lock()
        counters = {"swapped": 0, "no_face": 0}

        def _worker(dev_id: int, fa, fe, ge, pe):
            while True:
                item = in_q.get()
                if item is sentinel:
                    break
                idx, frame = item
                kps = None
                try:
                    if lean:
                        bboxes, kpss = fa.det_model.detect(
                            frame, max_num=0, metric="default", input_size=det_size
                        )
                        if bboxes is not None and len(bboxes) > 0:
                            areas = (bboxes[:, 2] - bboxes[:, 0]) * (
                                bboxes[:, 3] - bboxes[:, 1]
                            )
                            kps = kpss[int(np.argmax(areas))]
                    else:
                        f = _largest_face(fa.get(frame))
                        kps = f.kps if f is not None else None
                except Exception as exc:
                    logger.warning("data-parallel detect fail (cuda:%s): %s", dev_id, exc)
                if kps is None:
                    with lock:
                        results[idx] = frame
                        counters["no_face"] += 1
                    continue
                try:
                    out = fe.swap(
                        frame, kps, fast_latent,
                        gfpgan=ge, restore_weight=restore_weight, parser=pe,
                    )
                    with lock:
                        results[idx] = out
                        counters["swapped"] += 1
                except Exception as exc:
                    logger.warning("data-parallel swap fail (cuda:%s): %s", dev_id, exc)
                    with lock:
                        results[idx] = frame

        threads = []
        for d, (fa, fe, ge, pe) in zip(devices, workers):
            t = _th.Thread(target=_worker, args=(d, fa, fe, ge, pe),
                           name=f"ref_dp_{d}", daemon=True)
            t.start()
            threads.append(t)

        total = 0
        for frame in frame_iter:
            in_q.put((total, frame))
            total += 1
        for _ in threads:
            in_q.put(sentinel)
        for t in threads:
            t.join()

        raw_frames = [results[i] for i in range(total) if i in results]
        logger.info(
            "data-parallel: %d кадров на %d GPU %s",
            total, len(devices), devices,
        )
        return raw_frames, counters["swapped"], counters["no_face"]

    @classmethod
    def _parse_gpu_devices(cls) -> list[int]:
        """Список карт для data-parallel из настройки (фильтр по доступным CUDA)."""
        from app.config import settings

        raw = (settings.ref_video_gpu_devices or "").strip()
        if not raw:
            return []
        try:
            import torch

            n = torch.cuda.device_count() if torch.cuda.is_available() else 0
        except Exception:
            n = 0
        devs: list[int] = []
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                d = int(part)
            except ValueError:
                continue
            if 0 <= d < n and d not in devs:
                devs.append(d)
        return devs

    @classmethod
    def _build_worker(cls, dev_id: int):
        """Самодостаточный комплект движков на карте dev_id (детектор+inswapper+
        GFPGAN). Карта swap_device_id переиспользует уже резидентные singleton'ы."""
        from app.config import settings

        if dev_id in cls._workers:
            return cls._workers[dev_id]

        swap_dev = int(settings.ref_video_swap_device_id)
        if dev_id == swap_dev:
            face_app, _ = cls._load_models()
            worker = (
                face_app,
                cls._inswapper_fast,
                cls._load_gfpgan_onnx(),
                cls._load_face_parser(),
            )
            cls._workers[dev_id] = worker
            return worker

        from insightface.app import FaceAnalysis

        from app.generators.gfpgan_onnx import GfpganOnnxEngine
        from app.generators.inswapper import InswapperEngine

        _ensure_buffalo_l()
        _ensure_inswapper()
        providers = _onnx_providers(dev_id)
        fa = FaceAnalysis(
            name="buffalo_l", root=str(INSIGHTFACE_ROOT), providers=providers
        )
        fa.prepare(ctx_id=dev_id, det_size=(640, 640), det_thresh=0.4)
        fe = InswapperEngine(
            model_path=_abs_path(settings.inswapper_fast_model_path),
            providers=providers,
            device_id=dev_id,
            emap_source_path=_swapper_path(),
        )
        gpath = _abs_path(settings.ref_video_gfpgan_onnx_path)
        ge = GfpganOnnxEngine(
            model_path=gpath, providers=providers, device_id=dev_id
        )
        pe = None
        if bool(settings.ref_video_face_parser):
            from app.generators.face_parser_onnx import (
                FaceParserEngine,
                is_available as parser_ok,
            )

            ppath = _abs_path(settings.ref_video_parser_path)
            if parser_ok(ppath):
                pe = FaceParserEngine(
                    model_path=ppath, providers=providers, device_id=dev_id
                )
        logger.info(
            "ref_video: data-parallel worker resident on cuda:%s (det+inswapper+GFPGAN%s)",
            dev_id,
            "+parser" if pe is not None else "",
        )
        worker = (fa, fe, ge, pe)
        cls._workers[dev_id] = worker
        return worker

    @staticmethod
    def _process_ref_frame(
        frame: np.ndarray,
        target_kps: np.ndarray,
        *,
        simswap,
        simswap_identity,
        fast,
        fast_latent,
        swapper,
        source_face,
        target_face,
        gfpgan_onnx,
        restore_weight: float,
        do_restore: bool,
        parser=None,
    ) -> np.ndarray:
        """Один кадр: swap (+ опц. ONNX restore внутри rope_v1)."""
        if simswap is not None:
            return simswap.swap(frame, target_kps, simswap_identity)
        if fast is not None:
            return fast.swap(
                frame,
                target_kps,
                fast_latent,
                gfpgan=gfpgan_onnx if do_restore else None,
                restore_weight=restore_weight,
                parser=parser if do_restore else None,
            )
        return swapper.get(frame, target_face, source_face, paste_back=True)

    @staticmethod
    def _read_frames(cap, max_in: int):
        """Генератор кадров. При threaded-режиме декодирование идёт в отдельном
        потоке через очередь — перекрывает IO с GPU-работой главного потока."""
        from app.config import settings

        if not settings.ref_video_threaded_read:
            for _ in range(max_in):
                ok, frame = cap.read()
                if not ok:
                    break
                yield frame
            return

        import queue
        import threading

        q: queue.Queue = queue.Queue(maxsize=max(2, int(settings.ref_video_read_queue)))
        sentinel = object()

        def _reader():
            try:
                for _ in range(max_in):
                    ok, frame = cap.read()
                    if not ok:
                        break
                    q.put(frame)
            finally:
                q.put(sentinel)

        t = threading.Thread(target=_reader, name="ref_video_reader", daemon=True)
        t.start()
        while True:
            frame = q.get()
            if frame is sentinel:
                break
            yield frame
        t.join(timeout=1.0)

    def generate(
        self,
        source_image: Path,
        output_path: Path,
        *,
        width: int,
        height: int,
        fps: int,
        duration_sec: float,
        guest_profile=None,
    ) -> Path:
        from app.config import settings

        if not self.is_available():
            raise RuntimeError(
                "Ref-video: pip install insightface; при первом запуске скачается buffalo_l "
                "в models/insightface и inswapper_128.onnx"
            )

        t0 = time.perf_counter()
        pipeline = (settings.ref_video_pipeline or "legacy").strip().lower()
        face_app, swapper = self._load_models()

        src_bgr = cv2.cvtColor(
            np.array(Image.open(source_image).convert("RGB")),
            cv2.COLOR_RGB2BGR,
        )
        source_faces = face_app.get(src_bgr)
        source_face = _largest_face(source_faces)
        if source_face is None or source_face.normed_embedding is None:
            raise RuntimeError(
                "На фото гостя не найдено лицо (или нет embedding — переустановите buffalo_l)"
            )

        # SimSwap: identity-вектор источника считаем один раз (ArcFace по 5 точкам лица).
        simswap = type(self)._simswap
        simswap_identity = None
        if simswap is not None:
            simswap_identity = simswap.embed_identity(src_bgr, source_face.kps)

        # inswapper_fast: latent (emb @ emap) считаем один раз на гостя.
        fast = type(self)._inswapper_fast
        fast_latent = None
        if fast is not None:
            fast_latent = fast.embed_latent(source_face.normed_embedding)

        # Важно: REF_VIDEO_SWAP_WORKERS пока диагностический флаг. Текущий
        # InswapperEngine держит mutable io-binding buffers/latent state, поэтому
        # включать >1 без отдельного per-worker engine/context небезопасно.
        swap_workers = max(int(settings.ref_video_swap_workers), 1)
        if swap_workers > 1:
            logger.warning(
                "REF_VIDEO_SWAP_WORKERS=%d пока не активирован: shared swap engine "
                "не потокобезопасен; используем безопасный режим 1 worker",
                swap_workers,
            )
            swap_workers = 1

        duration = min(duration_sec, settings.liveportrait_driving_max_sec or duration_sec)
        driving_path = _pick_reference_mp4(guest_profile)

        with tempfile.TemporaryDirectory(prefix="gigavibe_ref_") as tmp:
            clip = _trim_reference_mp4(driving_path, Path(tmp), duration)

            cap = cv2.VideoCapture(str(clip))
            if not cap.isOpened():
                raise RuntimeError(f"Не открыть референс: {clip}")

            src_fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
            if src_fps < 1 or src_fps > 120:
                src_fps = 30.0
            max_in = max(int(round(duration * src_fps)), 1)
            use_src_fps = settings.ref_video_use_source_fps
            out_fps = int(round(src_fps)) if use_src_fps else fps
            out_n = max(int(round(duration * out_fps)), 1)

            # Декодирование кадров выносим в отдельный поток (приём Rope): пока GPU
            # свопает кадр N, ридер уже готовит N+1..N+k. GPU-вызовы остаются строго
            # в этом (главном) потоке — onnxruntime/insightface не потокобезопасны.
            frame_iter = self._read_frames(cap, max_in)

            raw_frames: list[np.ndarray] = []
            swapped = 0
            no_face = 0

            # Lean-детекция (приём Rope): для simswap/fast нужны только kps, поэтому
            # на каждом кадре зовём ТОЛЬКО детектор det_10g, а не весь buffalo_l (5 сетей).
            lean = (
                bool(settings.ref_video_lean_detect)
                and (simswap is not None or fast is not None)
                and getattr(face_app, "det_model", None) is not None
            )
            det_sz = max(int(settings.ref_video_det_size), 320)
            det_size = (det_sz, det_sz)

            # Инлайн-restore (приём Rope): GFPGAN прямо в swap-цикле по тем же kps,
            # без второго прохода по MP4 и без повторной RetinaFace-детекции.
            inline_restore = bool(settings.ref_video_face_restore) and bool(
                settings.ref_video_inline_restore
            )
            restorer = None
            restore_fn = None
            restore_weight = float(settings.ref_video_inline_restore_weight)
            restore_fp16 = bool(settings.ref_video_restore_fp16)
            restore_every_n = max(int(settings.ref_video_restore_every_n), 1)
            restore_interpolate = bool(settings.ref_video_restore_interpolate)
            restore_engine = (settings.ref_video_restore_engine or "facexlib").strip().lower()
            restore_backend = "facexlib"
            # Полностью-GPU режим (приём Rope): GFPGAN ONNX + diff-paste на GPU0
            # прямо в swap-потоке. Без CPU-paste, без parsenet, без воркеров.
            gfpgan_onnx = None
            face_parser = None
            rope_onnx_restore = (
                inline_restore
                and restore_engine == "onnx_512"
                and pipeline == "rope_v1"
            )
            if rope_onnx_restore:
                from app.generators.gfpgan_onnx import (
                    is_available as gfpgan_onnx_ok,
                )

                if gfpgan_onnx_ok(_abs_path(settings.ref_video_gfpgan_onnx_path)):
                    gfpgan_onnx = self._load_gfpgan_onnx()
                    face_parser = self._load_face_parser()
                if gfpgan_onnx is None:
                    logger.warning(
                        "onnx_512: GFPGANv1.4.onnx недоступен — fallback facexlib"
                    )
                    restore_engine = "facexlib"
                    rope_onnx_restore = False
                else:
                    restore_backend = "onnx_gpu"

            if inline_restore and not rope_onnx_restore:
                try:
                    from app.face_restore import (
                        _apply_residual,
                        _get_restorer,
                        is_available,
                        restore_frame_with_landmarks_residual,
                    )

                    if is_available():
                        restorer = _get_restorer()
                        restore_fn = restore_frame_with_landmarks_residual
                    else:
                        logger.warning("inline-restore: GFPGAN недоступен — пропуск")
                        inline_restore = False
                except Exception as exc:
                    logger.warning("inline-restore init fail: %s — без restore", exc)
                    inline_restore = False
            restored_n = 0
            restore_sec = 0.0
            swap_sec = 0.0

            # Data-parallel full-GPU: обе карты обрабатывают кадры независимо.
            devices = type(self)._parse_gpu_devices()
            data_parallel = (
                len(devices) > 1
                and rope_onnx_restore
                and fast is not None
            )
            if data_parallel:
                type(self).last_restore_strategy = f"data_parallel_{len(devices)}gpu"
                raw_frames, swapped, no_face = self._run_data_parallel(
                    devices,
                    frame_iter,
                    fast_latent,
                    restore_weight,
                    lean,
                    det_size,
                    int(settings.ref_video_read_queue),
                )
                inline_restore = False
                restored_n = swapped
            elif rope_onnx_restore:
                type(self).last_restore_strategy = "rope_gpu_onnx_inline"
            elif inline_restore:
                type(self).last_restore_strategy = (
                    f"inline_residual_every_{restore_every_n}"
                    if restore_every_n > 1
                    else "inline_full"
                )
            else:
                type(self).last_restore_strategy = None

            # Двухстадийный кросс-GPU конвейер (Rope): swap на GPU0, restore-воркеры на GPU1.
            pipelined = inline_restore and restore_fn is not None and not data_parallel
            rq = None
            if pipelined:
                import queue as _q
                import threading as _th

                from app.face_restore import _apply_residual

                rq = _q.Queue(maxsize=max(2, int(settings.ref_video_read_queue)))
                results: dict[int, tuple[np.ndarray, np.ndarray | None, bool]] = {}
                rsentinel = object()
                rstate = {"sec": 0.0, "n": 0, "first": None, "last": None}
                rlock = _th.Lock()
                n_workers = max(int(settings.ref_video_restore_workers), 1)
                restorers = [restorer]
                if restore_backend == "onnx":
                    # Один ONNX-движок на GPU1 (общий lock): несколько сессий = OOM.
                    n_workers = 1
                    restorers = [restorer]
                else:
                    from app.face_restore import new_restorer

                    for _wk in range(n_workers - 1):
                        try:
                            restorers.append(new_restorer())
                        except Exception as exc:
                            logger.warning("restore worker init fail (%s)", exc)
                            break

                rthreads = []

                def _restore_worker(my_restorer):
                    while True:
                        item = rq.get()
                        if item is rsentinel:
                            break
                        idx, fr, kps_r, residual_eligible = item
                        residual = None
                        if kps_r is not None:
                            try:
                                out, residual = restore_fn(
                                    fr, kps_r, my_restorer, restore_weight, restore_fp16
                                )
                            except Exception as exc:
                                logger.warning("inline-restore frame fail: %s", exc)
                                out = fr
                            now = time.perf_counter()
                            with rlock:
                                rstate["n"] += 1
                                if rstate["first"] is None:
                                    rstate["first"] = now
                                rstate["last"] = now
                            fr = out
                        with rlock:
                            results[idx] = (fr, residual, residual_eligible)

                for _wi, _r in enumerate(restorers):
                    _t = _th.Thread(target=_restore_worker, args=(_r,),
                                    name=f"ref_restore_{_wi}", daemon=True)
                    _t.start()
                    rthreads.append(_t)
                def _assemble_inline_results() -> list[np.ndarray]:
                    assembled: dict[int, np.ndarray] = {}
                    prev_res: np.ndarray | None = None
                    pending: list[tuple[int, np.ndarray, bool]] = []

                    def flush_pending(next_res: np.ndarray | None = None) -> None:
                        nonlocal pending
                        if not pending:
                            return
                        span = len(pending) + 1
                        for j, (pidx, pfr, eligible) in enumerate(pending, start=1):
                            if not eligible or prev_res is None:
                                assembled[pidx] = pfr
                            elif next_res is not None and restore_interpolate:
                                t = j / span
                                assembled[pidx] = _apply_residual(
                                    pfr, prev_res * (1.0 - t) + next_res * t
                                )
                            else:
                                assembled[pidx] = _apply_residual(pfr, prev_res)
                        pending = []

                    for ridx in range(out_idx):
                        fr, residual, eligible = results[ridx]
                        if residual is not None:
                            flush_pending(residual)
                            assembled[ridx] = fr
                            prev_res = residual
                        elif eligible:
                            pending.append((ridx, fr, eligible))
                        else:
                            assembled[ridx] = fr
                    flush_pending(None)
                    return [assembled[i] for i in range(out_idx)]

                type(self).last_restore_strategy = (
                    f"rope_dual_gpu_{restore_backend}_{len(rthreads)}w"
                )
                logger.info(
                    "dual-GPU pipeline (%s): swap cuda:%s, %d restore workers cuda:%s, every_n=%d",
                    restore_backend,
                    settings.ref_video_swap_device_id,
                    len(rthreads),
                    settings.ref_video_restore_device_id,
                    restore_every_n,
                )

            profile = bool(settings.ref_video_profile)
            prof = {"read": 0.0, "detect": 0.0, "swap": 0.0, "queue": 0.0}

            out_idx = 0  # порядковый индекс выходного кадра (для сборки по порядку)
            try:
                _t_read0 = time.perf_counter()
                for frame in frame_iter:
                    if profile:
                        prof["read"] += time.perf_counter() - _t_read0
                    t_swap0 = time.perf_counter()
                    target_kps = None
                    target_face = None
                    if lean:
                        bboxes, kpss = face_app.det_model.detect(
                            frame, max_num=0, metric="default", input_size=det_size
                        )
                        if bboxes is not None and len(bboxes) > 0:
                            # крупнейшее лицо по площади bbox
                            areas = (bboxes[:, 2] - bboxes[:, 0]) * (bboxes[:, 3] - bboxes[:, 1])
                            target_kps = kpss[int(np.argmax(areas))]
                    else:
                        target_face = _largest_face(face_app.get(frame))
                        target_kps = target_face.kps if target_face is not None else None
                    if profile:
                        prof["detect"] += time.perf_counter() - t_swap0

                    if target_kps is None:
                        no_face += 1
                        if pipelined:
                            rq.put((out_idx, frame, None, False))
                            out_idx += 1
                        else:
                            raw_frames.append(frame)
                        _t_read0 = time.perf_counter()
                        continue
                    try:
                        t_sw = time.perf_counter()
                        frame = self._process_ref_frame(
                            frame,
                            target_kps,
                            simswap=simswap,
                            simswap_identity=simswap_identity,
                            fast=fast,
                            fast_latent=fast_latent,
                            swapper=swapper,
                            source_face=source_face,
                            target_face=target_face,
                            gfpgan_onnx=gfpgan_onnx,
                            restore_weight=restore_weight,
                            do_restore=rope_onnx_restore,
                            parser=face_parser,
                        )
                        if profile:
                            prof["swap"] += time.perf_counter() - t_sw
                        swap_sec += time.perf_counter() - t_swap0
                        swapped += 1
                        if rope_onnx_restore:
                            restored_n += 1
                        if pipelined:
                            # restore по стрейдингу: каждый N-й свопнутый кадр.
                            # Остальные свопнутые кадры получают interpolated residual
                            # при ordered assembly после завершения restore-пула.
                            do_restore = (swapped - 1) % restore_every_n == 0
                            t_q = time.perf_counter()
                            rq.put((out_idx, frame, target_kps if do_restore else None, True))
                            if profile:
                                prof["queue"] += time.perf_counter() - t_q
                            out_idx += 1
                            _t_read0 = time.perf_counter()
                            continue
                    except Exception as exc:
                        logger.warning("swap frame failed: %s", exc)
                    if pipelined:
                        rq.put((out_idx, frame, None, False))
                        out_idx += 1
                    else:
                        raw_frames.append(frame)
                    _t_read0 = time.perf_counter()
            finally:
                cap.release()
                if pipelined:
                    for _ in rthreads:
                        rq.put(rsentinel)
                    for _t in rthreads:
                        _t.join()
                    # Время restore — wall-clock работы пула (last-first),
                    # а не сумма по воркерам (иначе при N>1 завышается).
                    if rstate["first"] is not None and rstate["last"] is not None:
                        restore_sec = rstate["last"] - rstate["first"]
                    restored_n = rstate["n"]
                    _t_asm = time.perf_counter()
                    raw_frames = _assemble_inline_results()
                    if profile:
                        prof["assemble"] = time.perf_counter() - _t_asm

        if not raw_frames:
            raise RuntimeError("Референс-ролик не дал кадров")

        if swapped == 0:
            raise RuntimeError(
                f"Лицо не подставлено ни на один кадр (нет лиц в ролике: {no_face}/{len(raw_frames)}). "
                "Проверьте референс: одно лицо в кадре, хороший свет."
            )

        from app.video_fit import effective_output_size, fit_frame_bgr

        fh, fw = raw_frames[0].shape[:2]
        out_w, out_h = effective_output_size(
            fw,
            fh,
            width,
            height,
            no_upscale=settings.ref_video_no_upscale,
        )

        if use_src_fps:
            out_fps = int(round(src_fps))
            out_n = len(raw_frames)
        elif len(raw_frames) > out_n:
            idx = np.linspace(0, len(raw_frames) - 1, out_n, dtype=int)
            raw_frames = [raw_frames[i] for i in idx]
        elif len(raw_frames) < out_n:
            raw_frames.extend([raw_frames[-1]] * (out_n - len(raw_frames)))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        _t_write = time.perf_counter()
        writer = cv2.VideoWriter(
            str(output_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            out_fps,
            (out_w, out_h),
        )
        for frame in raw_frames:
            writer.write(fit_frame_bgr(frame, out_w, out_h))
        writer.release()
        if profile:
            prof["write"] = time.perf_counter() - _t_write

        from app.video_encode import ensure_browser_mp4

        t_enc0 = time.perf_counter()
        ensure_browser_mp4(output_path, out_fps)
        encode_sec = time.perf_counter() - t_enc0
        elapsed = time.perf_counter() - t0
        type(self).last_generation_sec = elapsed
        report_swap = swap_sec
        if swap_sec <= 0 and restore_sec <= 0:
            # data-parallel / full-GPU: отдельные тайминги этапов не считаются.
            report_swap = max(0.0, elapsed - encode_sec)
        type(self).last_stage_timings = {
            "swap_s": round(report_swap, 3),
            "restore_s": round(restore_sec, 3),
            "encode_s": round(encode_sec, 3),
            "total_s": round(elapsed, 3),
        }
        if profile:
            type(self).last_stage_timings.update(
                {f"prof_{k}": round(v, 3) for k, v in prof.items()}
            )
            logger.info(
                "PROFILE: read=%.2f detect=%.2f swap=%.2f queue=%.2f "
                "assemble=%.2f write=%.2f restore(wall)=%.2f encode=%.2f total=%.2f",
                prof.get("read", 0.0),
                prof.get("detect", 0.0),
                prof.get("swap", 0.0),
                prof.get("queue", 0.0),
                prof.get("assemble", 0.0),
                prof.get("write", 0.0),
                restore_sec,
                encode_sec,
                elapsed,
            )
        # Инлайн-restore сделан внутри swap-цикла → pipeline пропустит 2-й проход.
        type(self).last_inline_restored = restored_n > 0
        type(self).last_restore_sec = restore_sec if restored_n > 0 else None
        provider = type(self).last_onnx_provider or "?"
        logger.info(
            "ref_video: %s, %.1f с — %dx%d @ %dfps, swap %s/%s, "
            "inline-restore %s/%s (%.1f с, %s), stages=%s, pipeline=%s (ref %.0fx%.0f)",
            provider,
            elapsed,
            out_w,
            out_h,
            out_fps,
            swapped,
            len(raw_frames),
            restored_n,
            swapped,
            restore_sec,
            type(self).last_restore_strategy,
            type(self).last_stage_timings,
            pipeline,
            fw,
            fh,
        )
        return output_path
