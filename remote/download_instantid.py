"""Скачать на D: всё для ключевого кадра InstantID:
  1) SDXL base                -> D:\\gigavibe-models\\sdxl-base
  2) InstantID controlnet+adapter -> D:\\gigavibe-models\\InstantID
  3) antelopev2 (5 onnx)      -> D:\\gigavibe-models\\insightface_antelope\\models\\antelopev2

Запуск на FARM (с токеном через cmd-обёртку download_instantid.cmd).
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

BASE = Path(r"D:\gigavibe-models")
SDXL_DIR = BASE / "sdxl-base"
INSTANTID_DIR = BASE / "InstantID"
ANTELOPE_DIR = BASE / "insightface_antelope" / "models" / "antelopev2"
HF_CACHE = BASE / "hf-cache"

os.environ.setdefault("HF_HOME", str(HF_CACHE))

ANTELOPE_FILES = [
    "1k3d68.onnx",
    "2d106det.onnx",
    "genderage.onnx",
    "glintr100.onnx",
    "scrfd_10g_bnkps.onnx",
]


def log(msg: str) -> None:
    print(msg, flush=True)


def dl_sdxl(token):
    from huggingface_hub import snapshot_download

    log(f"[1/3] SDXL base -> {SDXL_DIR}")
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
    log("    SDXL done.")


def dl_instantid(token):
    from huggingface_hub import hf_hub_download

    log(f"[2/3] InstantID -> {INSTANTID_DIR}")
    INSTANTID_DIR.mkdir(parents=True, exist_ok=True)
    for fn in [
        "ControlNetModel/config.json",
        "ControlNetModel/diffusion_pytorch_model.safetensors",
        "ip-adapter.bin",
    ]:
        hf_hub_download(
            repo_id="InstantX/InstantID",
            filename=fn,
            local_dir=str(INSTANTID_DIR),
            token=token,
        )
    log("    InstantID done.")


def dl_antelope(token):
    from huggingface_hub import hf_hub_download

    log(f"[3/3] antelopev2 -> {ANTELOPE_DIR}")
    ANTELOPE_DIR.mkdir(parents=True, exist_ok=True)
    for fn in ANTELOPE_FILES:
        path = hf_hub_download(
            repo_id="fofr/comfyui",
            filename=f"insightface/models/antelopev2/{fn}",
            local_dir=str(BASE / "_antelope_tmp"),
            token=token,
        )
        dst = ANTELOPE_DIR / fn
        shutil.copyfile(path, dst)
    log("    antelopev2 done.")


def main() -> int:
    token = os.environ.get("HF_TOKEN")
    log(f"HF_TOKEN: {'set' if token else 'none'}  HF_HOME={os.environ.get('HF_HOME')}")
    dl_sdxl(token)
    dl_instantid(token)
    dl_antelope(token)

    ok = (
        (SDXL_DIR / "model_index.json").exists()
        and (INSTANTID_DIR / "ip-adapter.bin").exists()
        and (ANTELOPE_DIR / "glintr100.onnx").exists()
    )
    log(f"ALL DONE ok={ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
