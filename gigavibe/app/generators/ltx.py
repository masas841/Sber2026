"""Локальный img2vid через LTX-Video (diffusers LTXImageToVideoPipeline)."""

import threading
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from app.generators.base import VideoGenerator
from app.generators.cinematic import _apply_festival_grade
from app.prompts import FESTIVAL_PROMPT, NEGATIVE_PROMPT

ROOT = Path(__file__).resolve().parent.parent.parent

_shared_pipe = None
_shared_model_id: str | None = None
# Пайплайн LTX один на процесс — сериализуем генерации, иначе параллельные запросы
# портят общее состояние (ошибки вида "index out of bounds").
_gen_lock = threading.Lock()


def warmup_model() -> None:
    if not LtxGenerator.is_available():
        return
    from app.config import settings

    gen = LtxGenerator(
        model_id=settings.ltx_model_id,
        num_frames=settings.ltx_num_frames,
        num_inference_steps=settings.ltx_inference_steps,
        guidance_scale=settings.ltx_guidance_scale,
        distilled=settings.ltx_distilled,
        gguf_repo_file=settings.ltx_gguf_repo_file,
    )
    gen._load_pipeline()


def _round_vae(size: int, divisor: int = 32) -> int:
    return max(divisor, size - (size % divisor))


def _snap_frames(count: int) -> int:
    """LTX: число кадров должно быть 8n+1. Округляем ВВЕРХ, чтобы не терять кадры
    (напр. запрос 250 → 257), минимум 9."""
    if count < 9:
        return 9
    if count % 8 == 1:
        return count
    return ((count - 1) // 8 + 1) * 8 + 1


def _ltx_model_dir() -> Path:
    """Папка весов LTX (settings.ltx_model_dir); относительный путь — от корня проекта."""
    from app.config import settings

    d = Path(settings.ltx_model_dir)
    if not d.is_absolute():
        d = ROOT / d
    return d


class LtxGenerator(VideoGenerator):
    def __init__(
        self,
        model_id: str,
        num_frames: int,
        num_inference_steps: int,
        guidance_scale: float,
        distilled: bool,
        gguf_repo_file: str | None = None,
    ) -> None:
        self.model_id = model_id
        self.num_frames = num_frames
        self.num_inference_steps = num_inference_steps
        self.guidance_scale = guidance_scale
        self.distilled = distilled
        self.gguf_repo_file = gguf_repo_file

    def _resolve_model_path(self) -> str:
        """Локальная папка с весами LTX (полная модель после download_ltx.bat)."""
        local_dir = _ltx_model_dir()
        marker = local_dir / "model_index.json"
        if marker.exists():
            return str(local_dir)

        from huggingface_hub import snapshot_download

        snapshot_download(
            repo_id=self.model_id,
            local_dir=str(local_dir),
        )
        return str(local_dir)

    @staticmethod
    def is_available() -> bool:
        try:
            import torch

            return torch.cuda.is_available()
        except ImportError:
            return False

    def _load_pipeline(self):
        global _shared_pipe, _shared_model_id

        if _shared_pipe is not None and _shared_model_id == self.model_id:
            return _shared_pipe

        import torch
        from diffusers import LTXImageToVideoPipeline

        dtype = torch.float16
        if torch.cuda.is_bf16_supported():
            dtype = torch.bfloat16

        local_full = (_ltx_model_dir() / "model_index.json").exists()
        transformer = None
        if self.gguf_repo_file and not local_full:
            from diffusers import GGUFQuantizationConfig, LTXVideoTransformer3DModel
            from huggingface_hub import hf_hub_download

            parts = self.gguf_repo_file.split("/")
            if len(parts) < 3:
                raise ValueError(
                    f"Неверный LTX_GGUF_REPO_FILE: {self.gguf_repo_file} "
                    "(формат: org/repo/filename.gguf)"
                )
            repo_id = "/".join(parts[:-1])
            filename = parts[-1]
            gguf_path = hf_hub_download(repo_id=repo_id, filename=filename)
            transformer = LTXVideoTransformer3DModel.from_single_file(
                gguf_path,
                quantization_config=GGUFQuantizationConfig(compute_dtype=dtype),
                torch_dtype=dtype,
            )

        model_path = self._resolve_model_path()
        load_kw: dict = {"torch_dtype": dtype}
        if transformer is not None:
            load_kw["transformer"] = transformer
        from app.config import settings

        pipe = LTXImageToVideoPipeline.from_pretrained(model_path, **load_kw)

        # Стратегия VRAM. На 24 ГБ карте LTX-2B (~10-12 ГБ) помещается целиком —
        # full даёт кратное ускорение против offload (тот гоняет слои CPU<->GPU).
        strategy = (settings.ltx_vram_strategy or "full").strip().lower()
        # Обратная совместимость: старый флаг sequential_offload форсит sequential.
        if strategy not in {"full", "model_offload", "sequential_offload"}:
            strategy = "sequential_offload" if settings.ltx_sequential_offload else "model_offload"

        dev_id = int(settings.ltx_device_id)
        if strategy == "full":
            pipe.to(f"cuda:{dev_id}")
            print(f"[GIGAvibe] LTX resident on cuda:{dev_id} (full, no offload)", flush=True)
        elif strategy == "model_offload":
            pipe.enable_model_cpu_offload(gpu_id=dev_id)
            print(f"[GIGAvibe] LTX model_cpu_offload on cuda:{dev_id}", flush=True)
        else:
            pipe.enable_sequential_cpu_offload(gpu_id=dev_id)
            print(f"[GIGAvibe] LTX sequential_cpu_offload on cuda:{dev_id}", flush=True)

        # VAE tiling оставляем всегда (декод видео — пик VRAM). Slicing нужен только
        # при offload; при full он не мешает, но и не обязателен.
        if strategy != "full" and hasattr(pipe, "enable_vae_slicing"):
            pipe.enable_vae_slicing()
        if strategy != "full" and hasattr(pipe, "enable_attention_slicing"):
            pipe.enable_attention_slicing("max")
        if hasattr(pipe, "vae") and hasattr(pipe.vae, "enable_tiling"):
            pipe.vae.enable_tiling()

        _shared_pipe = pipe
        _shared_model_id = self.model_id
        return _shared_pipe

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
        if not self.is_available():
            raise RuntimeError("CUDA/torch недоступны для LTX-Video")

        import torch

        import time

        from app.config import settings as cfg
        from app.ltx_quality import resolve_ltx_quality

        quality = resolve_ltx_quality(cfg)
        steps = max(self.num_inference_steps, quality.inference_steps)
        max_frames = max(self.num_frames, quality.max_frames)
        guidance = quality.guidance_scale
        decode_t = quality.decode_timestep
        decode_n = quality.decode_noise_scale

        # Сериализуем всю генерацию (InstantID keyframe + LTX) — общие синглтоны не потокобезопасны.
        with _gen_lock:
            pipe = self._load_pipeline()
            image = self._build_keyframe(source_image, width, height, cfg)

            if width >= height:
                cap_w, cap_h = quality.cap_landscape
            else:
                cap_w, cap_h = quality.cap_portrait
            gen_w = _round_vae(min(width, cap_w))
            gen_h = _round_vae(min(height, cap_h))
            if gen_h * gen_w > cap_w * cap_h:
                scale = ((cap_w * cap_h) / (gen_h * gen_w)) ** 0.5
                gen_w = _round_vae(int(gen_w * scale))
                gen_h = _round_vae(int(gen_h * scale))

            image = image.resize((gen_w, gen_h), Image.Resampling.LANCZOS)
            target_frames = _snap_frames(max(int(fps * duration_sec), 17))
            num_frames = min(target_frames, max_frames)

            prompt = cfg.ltx_prompt or FESTIVAL_PROMPT
            negative = cfg.ltx_negative_prompt or NEGATIVE_PROMPT

            seed = int(time.time() * 1000) % (2**31)
            gen = torch.Generator(device="cpu").manual_seed(seed)
            kwargs: dict = {
                "image": image,
                "prompt": prompt,
                "negative_prompt": negative,
                "width": gen_w,
                "height": gen_h,
                "num_frames": num_frames,
                "frame_rate": fps,
                "num_inference_steps": steps,
                "guidance_scale": guidance,
                "decode_timestep": decode_t,
                "decode_noise_scale": decode_n,
                "generator": gen,
                "output_type": "pil",
            }
            if cfg.ltx_guidance_rescale and cfg.ltx_guidance_rescale > 0:
                kwargs["guidance_rescale"] = float(cfg.ltx_guidance_rescale)
            if self.distilled:
                kwargs["timesteps"] = [1000, 993, 987, 981, 975, 909, 725, 0.03]
                kwargs["guidance_scale"] = 1.0

            try:
                result = pipe(**kwargs)
                frames = result.frames[0]
                if not frames or len(frames) < 2:
                    raise RuntimeError(
                        f"LTX вернул {len(frames) if frames else 0} кадров — нужно минимум 2 для движения"
                    )
                self._write_output_from_frames(frames, output_path, width, height, fps, duration_sec)
                del result, frames
            finally:
                import gc

                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

        from app.video_encode import ensure_browser_mp4

        ensure_browser_mp4(output_path, fps)
        return output_path

    def _build_keyframe(self, source_image: Path, width: int, height: int, cfg):
        """Стартовый кадр для LTX согласно cfg.keyframe_mode."""
        mode = (getattr(cfg, "keyframe_mode", "procedural") or "procedural").strip().lower()

        if mode == "instantid":
            from app.generators.keyframe_instantid import KeyframeInstantIDGenerator

            if KeyframeInstantIDGenerator.is_available():
                try:
                    from app.generators import keyframe_instantid

                    keyframe = KeyframeInstantIDGenerator().generate_keyframe(
                        source_image, width, height
                    )
                    # На одной карте — выгружаем SDXL+InstantID перед LTX (иначе не хватит VRAM).
                    # На 2+ картах (keyframe_keep_resident=true) держим InstantID резидентно на cuda:1,
                    # чтобы не перезагружать ~10 ГБ моделей на каждый запрос.
                    if not getattr(cfg, "keyframe_keep_resident", False):
                        keyframe_instantid.unload()
                    return keyframe
                except Exception as exc:
                    print(
                        f"[GIGAvibe] WARN: InstantID keyframe failed ({exc}); "
                        "fallback to procedural",
                        flush=True,
                    )
            else:
                print(
                    "[GIGAvibe] WARN: InstantID недоступен (модели/пайплайн); "
                    "fallback to procedural",
                    flush=True,
                )

        image = self.load_and_fit(source_image, width, height)
        if mode != "none" and cfg.festival_compose_scene:
            from app.festival_visual import compose_festival_still

            image = compose_festival_still(image, width, height)
        return image

    @staticmethod
    def _write_output_from_frames(
        frames: list,
        output_path: Path,
        width: int,
        height: int,
        fps: int,
        duration_sec: float,
    ) -> None:
        """Сборка MP4 из кадров LTX без seek по OpenCV (на Windows seek ломает движение)."""
        n_src = len(frames)
        target_count = max(int(fps * duration_sec), 1)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        if not writer.isOpened():
            raise RuntimeError("Не удалось создать выходной MP4")

        for i in range(target_count):
            if n_src == 1:
                idx = 0
            else:
                idx = round(i * (n_src - 1) / max(target_count - 1, 1))
            pil = frames[idx]
            if not hasattr(pil, "convert"):
                raise RuntimeError("Неверный формат кадра от LTX")
            rgb = np.array(pil.convert("RGB"))
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            writer.write(_apply_festival_grade(LtxGenerator._center_crop_resize(bgr, width, height)))

        writer.release()

    @staticmethod
    def _center_crop_resize(frame: np.ndarray, width: int, height: int) -> np.ndarray:
        h, w = frame.shape[:2]
        target_ratio = width / height
        src_ratio = w / h

        if src_ratio > target_ratio:
            new_w = int(h * target_ratio)
            x1 = (w - new_w) // 2
            crop = frame[:, x1 : x1 + new_w]
        else:
            new_h = int(w / target_ratio)
            y1 = (h - new_h) // 2
            crop = frame[y1 : y1 + new_h, :]

        return cv2.resize(crop, (width, height), interpolation=cv2.INTER_LANCZOS4)
