"""Стенд подбора параметров LTX с резидентными моделями на двух GPU.

- InstantID (SDXL+ControlNet+IP-Adapter+antelopev2) -> cuda:1, грузится ОДИН раз.
- LTX (T5+transformer+VAE) -> cuda:0 БЕЗ cpu-offload, грузится ОДИН раз и не выгружается.
- Ключевой кадр строится один раз и переиспользуется для всех конфигов свипа.
- Для каждого конфига пишем сырой MP4 (без грейда) + манифест JSON.

Запуск: см. run-ltxlab.cmd  (НЕ ставить CUDA_VISIBLE_DEVICES=0 — нужны обе карты).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image

ROOT = Path(r"C:\Users\user\gigavibe")
sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
from app.prompts import (  # noqa: E402
    FESTIVAL_PROMPT,
    KEYFRAME_FESTIVAL_PROMPT,
    KEYFRAME_NEGATIVE_PROMPT,
    NEGATIVE_PROMPT,
)

KF_DEVICE = "cuda:1"

# Промпт строго про ДВИЖЕНИЕ и камеру (без мета-инструкций и пересказа сцены), <128 токенов.
LTX_MOTION_PROMPT = (
    "A young woman at a summer music festival laughs and sways to the music, her hair and "
    "shoulders moving naturally. The handheld camera slowly pushes in with a gentle drift. "
    "Behind her, colorful stage spotlights sweep and twinkle, confetti drifts down through "
    "warm golden evening light, the blurred crowd shifts softly."
)
LTX_MOTION_NEGATIVE = (
    "static, frozen frame, no motion, morphing face, identity change, distorted face, "
    "deformed hands, extra fingers, blurry, overexposed, washed out, purple haze, "
    "flickering, low quality, watermark, text"
)

# V2: спокойнее — резкий фокус на субъекте, камера почти неподвижна, без слов про blur/push-in.
LTX_MOTION_PROMPT_V2 = (
    "A young woman at a music festival smiles and gently sways to the music, her hair moving "
    "softly. She stays centered and in sharp focus throughout. The camera is steady with only "
    "a very subtle handheld sway. Colorful stage lights twinkle behind her in the warm evening."
)
LTX_MOTION_NEGATIVE_V2 = (
    "out of focus, defocused, subject dissolving, fading away, bokeh blur over face, "
    "static, frozen frame, no motion, morphing face, identity change, distorted face, "
    "deformed hands, extra fingers, overexposed, washed out, flickering, low quality, watermark, text"
)

# V3: удержание фестивального фона — огни мигают ВСЁ ВРЕМЯ, цвета остаются яркими.
LTX_MOTION_PROMPT_V3 = (
    "A young woman at a vibrant music festival smiles and gently sways to the music, her hair "
    "moving softly, staying centered and in sharp focus. Behind her, bright multicolored stage "
    "lights keep flashing, sweeping and twinkling the entire time, the lively festival glow stays "
    "vivid and colorful. The camera is steady with a subtle handheld sway."
)
LTX_MOTION_NEGATIVE_V3 = (
    "sepia, faded background, dull colors, plain background, lights turning off, "
    "out of focus, defocused, subject dissolving, fading away, bokeh blur over face, "
    "static, frozen frame, no motion, morphing face, identity change, distorted face, "
    "deformed hands, overexposed, washed out, low quality, watermark, text"
)

FACE = ROOT / "data" / "test_face.jpg"
OUT_DIR = ROOT / "data" / "outputs" / "lab"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Размер генерации фиксируем для всех конфигов (портрет, кратно 32) — чтобы сравнивать честно.
# 512x896 ~ совпадает с рабочим профилем (cap 576x768) и не перегружает VAE-декод 257 кадров.
GEN_W, GEN_H = 512, 896
FPS = 25


def _abs(p) -> Path:
    p = Path(p)
    return p if p.is_absolute() else (ROOT / p)


def vram(tag: str) -> None:
    for i in range(torch.cuda.device_count()):
        free, total = torch.cuda.mem_get_info(i)
        used = (total - free) / 1024**3
        print(f"  [VRAM {tag}] gpu{i}: {used:.1f}/{total/1024**3:.0f} GB", flush=True)


# ---------------------------------------------------------------- InstantID (cuda:1)
def build_keyframe() -> Image.Image:
    cached = OUT_DIR / "keyframe.png"
    if cached.exists():
        print("keyframe: reuse cached", cached, flush=True)
        return Image.open(cached).convert("RGB").resize((GEN_W, GEN_H), Image.Resampling.LANCZOS)

    pipe_dir = _abs(settings.instantid_pipeline_dir)
    if str(pipe_dir) not in sys.path:
        sys.path.insert(0, str(pipe_dir))

    from diffusers.models import ControlNetModel
    from insightface.app import FaceAnalysis
    from pipeline_stable_diffusion_xl_instantid import (  # type: ignore
        StableDiffusionXLInstantIDPipeline,
        draw_kps,
    )

    dtype = torch.float16
    antelope_root = _abs(settings.instantid_antelope_root)
    face_app = FaceAnalysis(
        name="antelopev2",
        root=str(antelope_root),
        providers=[("CUDAExecutionProvider", {"device_id": 1}), "CPUExecutionProvider"],
    )
    face_app.prepare(ctx_id=1, det_size=(640, 640))

    repo = _abs(settings.instantid_repo_dir)
    controlnet = ControlNetModel.from_pretrained(str(repo / "ControlNetModel"), torch_dtype=dtype)

    base_dir = _abs(settings.instantid_base_dir)
    base = (
        str(base_dir)
        if (base_dir / "model_index.json").exists()
        else settings.instantid_base_model
    )
    pipe = StableDiffusionXLInstantIDPipeline.from_pretrained(
        base, controlnet=controlnet, torch_dtype=dtype, variant="fp16"
    )
    pipe.load_ip_adapter_instantid(str(repo / "ip-adapter.bin"))
    pipe.to(KF_DEVICE)
    try:
        pipe.vae.enable_tiling()
    except Exception:
        pass

    vram("after InstantID load")

    img = Image.open(FACE).convert("RGB")
    bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    faces = face_app.get(bgr)
    if not faces:
        raise RuntimeError("InstantID: лицо не найдено")
    face = sorted(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))[-1]
    kps_img = draw_kps(img, face["kps"]).resize((GEN_W, GEN_H), Image.Resampling.LANCZOS)

    result = pipe(
        prompt=settings.instantid_prompt or KEYFRAME_FESTIVAL_PROMPT,
        negative_prompt=settings.instantid_negative_prompt or KEYFRAME_NEGATIVE_PROMPT,
        image_embeds=face["embedding"],
        image=kps_img,
        controlnet_conditioning_scale=float(settings.instantid_controlnet_scale),
        ip_adapter_scale=float(settings.instantid_ip_scale),
        num_inference_steps=int(settings.instantid_steps),
        guidance_scale=float(settings.instantid_guidance),
        width=GEN_W,
        height=GEN_H,
    )
    kf = result.images[0]
    kf.save(OUT_DIR / "keyframe.png")
    # InstantID НЕ выгружаем — проверяем резидентность обеих моделей.
    return kf


# ---------------------------------------------------------------- LTX (cuda:0, резидентно)
def load_ltx():
    from diffusers import LTXImageToVideoPipeline

    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    pipe = LTXImageToVideoPipeline.from_pretrained(str(settings.ltx_model_dir), torch_dtype=dtype)
    # cpu_offload: модель «тёплая» в RAM (без перечтения с диска между конфигами),
    # а на время VAE-декода 257 кадров трансформер/T5 уходят с GPU -> декод влезает в 24 ГБ.
    pipe.enable_model_cpu_offload(gpu_id=0)
    try:
        pipe.vae.enable_tiling()
    except Exception:
        pass
    if hasattr(pipe, "enable_vae_slicing"):
        pipe.enable_vae_slicing()
    vram("after LTX load")
    return pipe


def write_mp4(frames: list, path: Path) -> None:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    w, h = frames[0].size
    writer = cv2.VideoWriter(str(path), fourcc, FPS, (w, h))
    for pil in frames:
        bgr = cv2.cvtColor(np.array(pil.convert("RGB")), cv2.COLOR_RGB2BGR)
        writer.write(bgr)
    writer.release()


def run_config(pipe, keyframe: Image.Image, cfg: dict) -> dict:
    seed = cfg.get("seed", 12345)
    gen = torch.Generator(device="cpu").manual_seed(seed)
    t = time.time()
    result = pipe(
        image=keyframe,
        prompt=cfg.get("prompt", LTX_MOTION_PROMPT),
        negative_prompt=cfg.get("neg", LTX_MOTION_NEGATIVE),
        width=GEN_W,
        height=GEN_H,
        num_frames=cfg["frames"],
        frame_rate=FPS,
        num_inference_steps=cfg["steps"],
        guidance_scale=cfg["guidance"],
        guidance_rescale=cfg.get("gr", 0.0),
        decode_timestep=cfg["dt"],
        decode_noise_scale=cfg["dn"],
        generator=gen,
        output_type="pil",
    )
    frames = result.frames[0]
    out = OUT_DIR / f"lab_{cfg['tag']}.mp4"
    write_mp4(frames, out)
    dt = round(time.time() - t, 1)
    del result, frames
    torch.cuda.empty_cache()
    info = {**cfg, "out": str(out), "sec": dt, "size": out.stat().st_size}
    print("DONE", json.dumps(info, ensure_ascii=False), flush=True)
    return info


CONFIGS = [
    # Удержание фона: V3-промпт (огни мигают всё время) + высокий guidance с компенсацией gr, 121к/5с.
    {"tag": "M_g4_gr5", "frames": 121, "steps": 40, "guidance": 4.0, "gr": 0.5, "dt": 0.05, "dn": 0.025,
     "prompt": LTX_MOTION_PROMPT_V3, "neg": LTX_MOTION_NEGATIVE_V3},
    {"tag": "N_g5_gr7", "frames": 121, "steps": 40, "guidance": 5.0, "gr": 0.7, "dt": 0.05, "dn": 0.025,
     "prompt": LTX_MOTION_PROMPT_V3, "neg": LTX_MOTION_NEGATIVE_V3},
    {"tag": "O_g4_gr3", "frames": 121, "steps": 40, "guidance": 4.0, "gr": 0.3, "dt": 0.05, "dn": 0.025,
     "prompt": LTX_MOTION_PROMPT_V3, "neg": LTX_MOTION_NEGATIVE_V3},
    {"tag": "P_g35_gr4", "frames": 121, "steps": 40, "guidance": 3.5, "gr": 0.4, "dt": 0.05, "dn": 0.025,
     "prompt": LTX_MOTION_PROMPT_V3, "neg": LTX_MOTION_NEGATIVE_V3},
]


def main():
    vram("start")
    keyframe = build_keyframe()
    pipe = load_ltx()
    manifest = []
    for cfg in CONFIGS:
        try:
            manifest.append(run_config(pipe, keyframe, cfg))
        except Exception as exc:
            print("FAIL", cfg["tag"], repr(exc), flush=True)
            manifest.append({**cfg, "error": repr(exc)})
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
