"""
Festival portrait через внешний API (Nano Banana / nana-banana).

Бэкенды:
  aitunnel — AITunnel /v1/images/edits (gemini-3.1-flash-image-preview, ~15–40с, без VPN)
  quatarly — Quatarly OpenAI-compat
  gemini   — Google Gemini API напрямую
  proxy    — nanobananaapi.ai (async poll, ~100с)
"""

from __future__ import annotations

import io
import logging
import time
from pathlib import Path

from PIL import Image

from app.generators.base import VideoGenerator

logger = logging.getLogger(__name__)


class FestivalNanobananaGenerator(VideoGenerator):
    last_generation_sec: float | None = None
    last_stage_timings: dict[str, float] | None = None

    @classmethod
    def backend(cls) -> str:
        from app.config import settings

        return (settings.nanobanana_backend or "aitunnel").strip().lower()

    @classmethod
    def is_available(cls) -> bool:
        from app.config import settings

        backend = cls.backend()
        if backend == "proxy":
            return bool((settings.nanobanana_api_key or "").strip())
        if backend == "aitunnel":
            return bool((settings.aitunnel_api_key or "").strip())
        if backend == "quatarly":
            return bool((settings.quatarly_api_key or "").strip())
        if not (settings.gemini_api_key or "").strip():
            return False
        try:
            from google import genai  # noqa: F401
        except ImportError:
            return False
        return True

    @staticmethod
    def install_hint() -> str:
        return (
            "Nano Banana: AITUNNEL_API_KEY + NANOBANANA_BACKEND=aitunnel, "
            "или QUATARLY_API_KEY (backend=quatarly), "
            "GEMINI_API_KEY (backend=gemini), "
            "NANOBANANA_API_KEY (backend=proxy). "
            "См. scripts/test_nanobanana.py"
        )

    def _generate_aitunnel(
        self,
        source_image: Path,
        prompt: str,
        width: int,
        height: int,
    ) -> tuple[Image.Image, dict[str, float]]:
        from app.config import settings
        from app.aitunnel_image_client import generate_festival_portrait

        t0 = time.perf_counter()
        still = generate_festival_portrait(
            api_key=(settings.aitunnel_api_key or "").strip(),
            base_url=settings.aitunnel_api_base_url,
            model=settings.nanobanana_model,
            prompt=prompt,
            source_image=source_image,
            aspect_ratio=settings.nanobanana_aspect_ratio,
            image_size=settings.nanobanana_image_size,
        )
        gen_sec = time.perf_counter() - t0
        if still.size != (width, height):
            still = still.resize((width, height), Image.Resampling.LANCZOS)
        return still, {"aitunnel_api_s": round(gen_sec, 3), "nanobanana_total_s": round(gen_sec, 3)}

    def _generate_quatarly(
        self,
        source_image: Path,
        prompt: str,
        width: int,
        height: int,
    ) -> tuple[Image.Image, dict[str, float]]:
        from app.config import settings
        from app.quatarly_image_client import generate_festival_portrait

        t0 = time.perf_counter()
        still = generate_festival_portrait(
            api_key=(settings.quatarly_api_key or "").strip(),
            base_url=settings.quatarly_api_base_url,
            model=settings.nanobanana_model,
            prompt=prompt,
            source_image=source_image,
            aspect_ratio=settings.nanobanana_aspect_ratio,
            image_size=settings.nanobanana_image_size,
        )
        gen_sec = time.perf_counter() - t0
        if still.size != (width, height):
            still = still.resize((width, height), Image.Resampling.LANCZOS)
        return still, {"quatarly_api_s": round(gen_sec, 3), "nanobanana_total_s": round(gen_sec, 3)}

    def _generate_gemini(
        self,
        source_image: Path,
        prompt: str,
        width: int,
        height: int,
    ) -> tuple[Image.Image, dict[str, float]]:
        from app.config import settings
        from app.gemini_image_client import generate_festival_portrait

        t0 = time.perf_counter()
        still = generate_festival_portrait(
            api_key=(settings.gemini_api_key or "").strip(),
            model=settings.nanobanana_model,
            prompt=prompt,
            source_image=source_image,
            aspect_ratio=settings.nanobanana_aspect_ratio,
            image_size=settings.nanobanana_image_size,
            base_url=(settings.gemini_api_base_url or "").strip() or None,
        )
        gen_sec = time.perf_counter() - t0
        if still.size != (width, height):
            still = still.resize((width, height), Image.Resampling.LANCZOS)
        return still, {"gemini_api_s": round(gen_sec, 3), "nanobanana_total_s": round(gen_sec, 3)}

    def _generate_proxy(
        self,
        source_image: Path,
        prompt: str,
        width: int,
        height: int,
    ) -> tuple[Image.Image, dict[str, float]]:
        from app.config import settings
        from app.nanobanana_client import NanoBananaApiClient, publish_source_image_url

        api_key = (settings.nanobanana_api_key or "").strip()
        client = NanoBananaApiClient(api_key, settings.nanobanana_api_base_url)

        t0 = time.perf_counter()
        upload_sec = 0.0
        submit_sec = 0.0
        poll_sec = 0.0

        t_upload = time.perf_counter()
        image_url = publish_source_image_url(source_image)
        upload_sec = time.perf_counter() - t_upload
        logger.info("nanobanana source url=%s prompt=%s…", image_url[:80], prompt[:160])

        t_submit = time.perf_counter()
        api_version = (settings.nanobanana_api_version or "v2").strip().lower()
        if api_version in {"v2", "2", "generate-2"}:
            task_id = client.submit_generate_v2(
                prompt,
                image_urls=[image_url],
                aspect_ratio=settings.nanobanana_aspect_ratio,
                resolution=settings.nanobanana_image_size,
                output_format="png",
            )
        else:
            task_id = client.submit_generate_v1(
                prompt,
                image_urls=[image_url],
                image_size=settings.nanobanana_aspect_ratio,
            )
        submit_sec = time.perf_counter() - t_submit
        logger.info("nanobanana taskId=%s", task_id)

        t_poll = time.perf_counter()
        result_url = client.wait_for_result(
            task_id,
            poll_sec=settings.nanobanana_poll_sec,
            timeout_sec=settings.nanobanana_timeout_sec,
        )
        poll_sec = time.perf_counter() - t_poll

        raw = client.download_bytes(result_url)
        still = Image.open(io.BytesIO(raw)).convert("RGB")
        if still.size != (width, height):
            still = still.resize((width, height), Image.Resampling.LANCZOS)

        gen_sec = time.perf_counter() - t0
        return still, {
            "nanobanana_upload_s": round(upload_sec, 3),
            "nanobanana_submit_s": round(submit_sec, 3),
            "nanobanana_poll_s": round(poll_sec, 3),
            "nanobanana_total_s": round(gen_sec, 3),
        }

    @staticmethod
    def _is_quatarly_network_error(exc: BaseException) -> bool:
        msg = str(exc).lower()
        needles = (
            "eof occurred",
            "unexpected_eof",
            "disconnected",
            "remoteprotocol",
            "readtimeout",
            "urlopen error",
            "ssl",
            "таймаут vpn",
            "обрыв",
        )
        return any(n in msg for n in needles)

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
        from app.prompts import build_nanobanana_prompt

        del fps, duration_sec

        prompt = build_nanobanana_prompt(guest_profile)
        if settings.nanobanana_prompt:
            prompt = settings.nanobanana_prompt

        backend = self.backend()
        job_label = source_image.parent.name or source_image.stem
        logger.info(
            "nanobanana job=%s backend=%s model=%s aspect=%s image_size=%s prompt_len=%s",
            job_label,
            backend,
            settings.nanobanana_model,
            settings.nanobanana_aspect_ratio,
            settings.nanobanana_image_size,
            len(prompt),
        )
        t0 = time.perf_counter()
        if backend == "proxy":
            still, timings = self._generate_proxy(source_image, prompt, width, height)
            log_label = "nanobanana proxy"
        elif backend == "aitunnel":
            still, timings = self._generate_aitunnel(source_image, prompt, width, height)
            log_label = "aitunnel"
        elif backend == "quatarly":
            try:
                still, timings = self._generate_quatarly(source_image, prompt, width, height)
                log_label = "quatarly"
            except RuntimeError as exc:
                from app.config import settings

                proxy_key = (settings.nanobanana_api_key or "").strip()
                if (
                    settings.nanobanana_fallback_to_proxy
                    and proxy_key
                    and self._is_quatarly_network_error(exc)
                ):
                    logger.warning("quatarly failed (%s) — fallback to nanobanana proxy", exc)
                    still, timings = self._generate_proxy(source_image, prompt, width, height)
                    timings["quatarly_fallback"] = 1.0
                    log_label = "nanobanana proxy (fallback)"
                else:
                    raise
        else:
            still, timings = self._generate_gemini(source_image, prompt, width, height)
            log_label = "gemini"

        out = output_path if output_path.suffix.lower() in {".jpg", ".jpeg"} else output_path.with_suffix(".jpg")
        out.parent.mkdir(parents=True, exist_ok=True)
        still.save(out, format="JPEG", quality=settings.nanobanana_jpeg_quality, optimize=True)

        gen_sec = time.perf_counter() - t0
        type(self).last_generation_sec = gen_sec
        type(self).last_stage_timings = timings
        logger.info("%s done: %.1fs -> %s", log_label, gen_sec, out.name)
        return out
