"""
Скачать модели festival_toon (PuLID-FLUX fp8) в gigavibe/models/.

  models/flux-dev-fp8.safetensors
  models/flux_dev_quantization_map.json
  models/ae.safetensors
  models/pulid_flux_v0.9.1.safetensors

HF_TOKEN в .env обязателен (FLUX.1-dev gated).

  .venv\\Scripts\\python.exe scripts\\download_festival_toon_models.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MODELS = ROOT / "models"
PULID_VERSION = "v0.9.1"


def log(msg: str) -> None:
    print(msg, flush=True)


def _require_token() -> str:
    token: str | None = None
    try:
        from app.config import settings

        token = settings.hf_token
    except Exception:
        pass
    token = (token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or "").strip()
    if not token:
        log("ERROR: HF_TOKEN не задан в .env")
        raise SystemExit(1)
    os.environ["HF_TOKEN"] = token
    os.environ["HUGGING_FACE_HUB_TOKEN"] = token
    try:
        from huggingface_hub import login

        login(token=token, add_to_git_credential=False)
    except Exception as exc:
        log(f"WARN: login: {exc}")
    masked = f"hf_…{token[-4:]}" if len(token) > 8 else "(set)"
    log(f"HF_TOKEN: {masked}")
    return token


def main() -> int:
    from huggingface_hub import hf_hub_download

    MODELS.mkdir(parents=True, exist_ok=True)
    token = _require_token()

    log("[flux-fp8] XLabs-AI/flux-dev-fp8")
    hf_hub_download(
        "XLabs-AI/flux-dev-fp8",
        "flux-dev-fp8.safetensors",
        local_dir=str(MODELS),
        token=token,
    )
    hf_hub_download(
        "XLabs-AI/flux-dev-fp8",
        "flux_dev_quantization_map.json",
        local_dir=str(MODELS),
        token=token,
    )

    log("[ae] black-forest-labs/FLUX.1-dev ae.safetensors")
    hf_hub_download(
        "black-forest-labs/FLUX.1-dev",
        "ae.safetensors",
        local_dir=str(MODELS),
        token=token,
    )

    log(f"[pulid] guozinan/PuLID pulid_flux_{PULID_VERSION}.safetensors")
    hf_hub_download(
        "guozinan/PuLID",
        f"pulid_flux_{PULID_VERSION}.safetensors",
        local_dir=str(MODELS),
        token=token,
    )

    antelope_link = MODELS / "antelopev2"
    antelope_src = MODELS / "insightface_antelope" / "models" / "antelopev2"
    if not antelope_link.exists() and antelope_src.exists():
        log(f"NOTE: создайте junction models/antelopev2 -> {antelope_src}")

    ok = all(
        (MODELS / name).exists()
        for name in (
            "flux-dev-fp8.safetensors",
            "flux_dev_quantization_map.json",
            "ae.safetensors",
            f"pulid_flux_{PULID_VERSION}.safetensors",
        )
    )
    log(f"verify ok={ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
