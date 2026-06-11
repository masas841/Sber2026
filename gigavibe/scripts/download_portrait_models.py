"""
Скачать модели festival_portrait в gigavibe/models/ (с Hugging Face, не с FARM).

  models/sdxl-base
  models/InstantID
  models/insightface_antelope/models/antelopev2

Токен: HF_TOKEN в .env (или переменная окружения).

  .venv\\Scripts\\python.exe scripts\\download_portrait_models.py
  .venv\\Scripts\\python.exe scripts\\download_portrait_models.py --only instantid antelope
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MODELS = ROOT / "models"
SDXL_DIR = MODELS / "sdxl-base"
INSTANTID_DIR = MODELS / "InstantID"
ANTELOPE_DIR = MODELS / "insightface_antelope" / "models" / "antelopev2"
HF_CACHE = MODELS / "hf-cache"

ANTELOPE_FILES = (
    "1k3d68.onnx",
    "2d106det.onnx",
    "genderage.onnx",
    "glintr100.onnx",
    "scrfd_10g_bnkps.onnx",
)


def log(msg: str) -> None:
    print(msg, flush=True)


def _require_token() -> str:
    """HF_TOKEN из .env (app.config) или окружения — обязателен для SDXL/InstantID."""
    token: str | None = None
    try:
        from app.config import settings

        token = settings.hf_token
    except Exception:
        pass
    token = (token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or "").strip()
    if not token:
        log("ERROR: HF_TOKEN не задан.")
        log("Добавьте в gigavibe/.env строку HF_TOKEN=hf_...")
        raise SystemExit(1)

    os.environ["HF_TOKEN"] = token
    os.environ["HUGGING_FACE_HUB_TOKEN"] = token
    try:
        from huggingface_hub import login

        login(token=token, add_to_git_credential=False)
    except Exception as exc:
        log(f"WARN: huggingface_hub.login: {exc}")

    masked = f"hf_…{token[-4:]}" if len(token) > 8 else "(set)"
    log(f"HF_TOKEN: {masked}")
    return token


def dl_sdxl(token: str | None) -> None:
    from huggingface_hub import snapshot_download

    log(f"[sdxl] -> {SDXL_DIR}")
    SDXL_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id="stabilityai/stable-diffusion-xl-base-1.0",
        local_dir=str(SDXL_DIR),
        token=token,
        max_workers=4,
        allow_patterns=[
            "model_index.json",
            "scheduler/*",
            "text_encoder/*",
            "text_encoder_2/*",
            "tokenizer/*",
            "tokenizer_2/*",
            "unet/*.json",
            "unet/diffusion_pytorch_model.fp16.safetensors",
            "vae/*.json",
            "vae/diffusion_pytorch_model.fp16.safetensors",
        ],
    )
    log("[sdxl] done")


def dl_instantid(token: str | None) -> None:
    from huggingface_hub import hf_hub_download

    log(f"[instantid] -> {INSTANTID_DIR}")
    INSTANTID_DIR.mkdir(parents=True, exist_ok=True)
    for fn in (
        "ControlNetModel/config.json",
        "ControlNetModel/diffusion_pytorch_model.safetensors",
        "ip-adapter.bin",
    ):
        hf_hub_download(
            repo_id="InstantX/InstantID",
            filename=fn,
            local_dir=str(INSTANTID_DIR),
            token=token,
        )
    log("[instantid] done")


def dl_antelope(token: str | None) -> None:
    from huggingface_hub import hf_hub_download

    log(f"[antelopev2] -> {ANTELOPE_DIR}")
    ANTELOPE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = MODELS / "_antelope_tmp"
    for fn in ANTELOPE_FILES:
        path = hf_hub_download(
            repo_id="fofr/comfyui",
            filename=f"insightface/models/antelopev2/{fn}",
            local_dir=str(tmp),
            token=token,
        )
        shutil.copyfile(path, ANTELOPE_DIR / fn)
    shutil.rmtree(tmp, ignore_errors=True)
    log("[antelopev2] done")


def verify() -> bool:
    ok = (
        (SDXL_DIR / "model_index.json").exists()
        and (INSTANTID_DIR / "ip-adapter.bin").exists()
        and (ANTELOPE_DIR / "glintr100.onnx").exists()
    )
    log(f"verify ok={ok}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--only",
        nargs="+",
        choices=["sdxl", "instantid", "antelope"],
        help="скачать только указанные части",
    )
    args = ap.parse_args()

    os.environ.setdefault("HF_HOME", str(HF_CACHE))
    HF_CACHE.mkdir(parents=True, exist_ok=True)

    log(f"HF_HOME={HF_CACHE}")
    token = _require_token()

    steps = args.only or ["instantid", "antelope", "sdxl"]
    if "instantid" in steps:
        dl_instantid(token)
    if "antelope" in steps:
        dl_antelope(token)
    if "sdxl" in steps:
        dl_sdxl(token)

    return 0 if verify() else 1


if __name__ == "__main__":
    raise SystemExit(main())
