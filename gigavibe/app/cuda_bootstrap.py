"""CUDA/cuDNN для onnxruntime-gpu до любых InferenceSession (киоск + тесты)."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)
_bootstrapped = False


def ensure_onnx_cuda() -> None:
    global _bootstrapped
    if _bootstrapped:
        return
    _bootstrapped = True

    if sys.platform == "win32":
        try:
            import torch

            lib = Path(torch.__file__).resolve().parent / "lib"
            if lib.is_dir():
                lib_s = str(lib)
                os.environ["PATH"] = lib_s + os.pathsep + os.environ.get("PATH", "")
                os.add_dll_directory(lib_s)
        except Exception as exc:
            logger.warning("cuda_bootstrap: torch lib PATH: %s", exc)

    try:
        import onnxruntime as ort

        preload = getattr(ort, "preload_dlls", None)
        if callable(preload):
            preload(cuda=True, cudnn=True)
    except Exception as exc:
        logger.warning("cuda_bootstrap: onnxruntime preload_dlls: %s", exc)


ensure_onnx_cuda()
