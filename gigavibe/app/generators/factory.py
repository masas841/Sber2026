from app.config import settings
from app.generators.base import VideoGenerator
from app.generators.cinematic import CinematicGenerator
from app.generators.liveportrait import LivePortraitGenerator
from app.generators.ref_video import RefVideoGenerator
from app.generators.festival_portrait import FestivalPortraitGenerator
from app.generators.festival_toon import FestivalToonGenerator
from app.generators.festival_nanobanana import FestivalNanobananaGenerator
from app.generators.ltx import LtxGenerator
from app.generators.svd import SvdGenerator


def _svd() -> VideoGenerator:
    if not SvdGenerator.is_available():
        raise RuntimeError("SVD: torch/CUDA не установлены")
    return SvdGenerator(
        model_id=settings.svd_model_id,
        num_frames=settings.svd_num_frames,
        decode_chunk_size=settings.svd_decode_chunk_size,
        inference_steps=settings.svd_inference_steps,
    )


def _ref_video() -> VideoGenerator:
    if not RefVideoGenerator.is_available():
        raise RuntimeError(
            "Ref-video: pip install insightface и веса inswapper (models/inswapper_128.onnx)"
        )
    return RefVideoGenerator()


def _liveportrait() -> VideoGenerator:
    if not LivePortraitGenerator.is_available():
        raise RuntimeError(
            "LivePortrait не установлен. " + LivePortraitGenerator.install_hint()
        )
    return LivePortraitGenerator()


def _ltx() -> VideoGenerator:
    if not LtxGenerator.is_available():
        raise RuntimeError("LTX: torch/CUDA не установлены")
    return LtxGenerator(
        model_id=settings.ltx_model_id,
        num_frames=settings.ltx_num_frames,
        num_inference_steps=settings.ltx_inference_steps,
        guidance_scale=settings.ltx_guidance_scale,
        distilled=settings.ltx_distilled,
        gguf_repo_file=settings.ltx_gguf_repo_file,
    )


def _festival_portrait() -> VideoGenerator:
    if not FestivalPortraitGenerator.is_available():
        raise RuntimeError("Festival portrait: " + FestivalPortraitGenerator.install_hint())
    return FestivalPortraitGenerator()


def _festival_toon() -> VideoGenerator:
    if not FestivalToonGenerator.is_available():
        raise RuntimeError("Festival toon: " + FestivalToonGenerator.install_hint())
    return FestivalToonGenerator()


def _festival_nanobanana() -> VideoGenerator:
    if not FestivalNanobananaGenerator.is_available():
        raise RuntimeError("Nano Banana: " + FestivalNanobananaGenerator.install_hint())
    return FestivalNanobananaGenerator()


def get_generator() -> VideoGenerator:
    mode = settings.generator_mode.lower()

    if mode == "cinematic":
        return CinematicGenerator()
    if mode == "svd":
        return _svd()
    if mode == "ltx":
        return _ltx()
    if mode == "liveportrait":
        return _liveportrait()
    if mode in {"festival_portrait", "portrait", "portrait_still"}:
        return _festival_portrait()
    if mode in {"festival_toon", "toon", "portrait_toon"}:
        return _festival_toon()
    if mode in {"nanobanana", "nano_banana", "festival_nanobanana", "nana_banana"}:
        return _festival_nanobanana()
    if mode in {"ref_video", "refvideo", "faceswap"}:
        return _ref_video()

    # auto: nanobanana → toon → portrait → ref_video → ltx → svd → cinematic
    if FestivalNanobananaGenerator.is_available():
        return _festival_nanobanana()
    if FestivalToonGenerator.is_available():
        return _festival_toon()
    if FestivalPortraitGenerator.is_available():
        return _festival_portrait()
    if RefVideoGenerator.is_available():
        return _ref_video()
    if LtxGenerator.is_available():
        return _ltx()
    if SvdGenerator.is_available():
        return _svd()
    return CinematicGenerator()
