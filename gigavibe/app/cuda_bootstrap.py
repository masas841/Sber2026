"""CUDA/cuDNN для onnxruntime-gpu до любых InferenceSession (киоск + тесты)."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)
_bootstrapped = False
_dll_dir_handles = []


def _prepend_path(path: Path) -> None:
    path_s = str(path)
    parts = os.environ.get("PATH", "").split(os.pathsep)
    if path_s not in parts:
        os.environ["PATH"] = path_s + os.pathsep + os.environ.get("PATH", "")


def _add_dll_directory(path: Path) -> None:
    if not path.is_dir():
        return
    _prepend_path(path)
    if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
        # Keep the returned handle alive; otherwise Windows can drop the DLL path.
        _dll_dir_handles.append(os.add_dll_directory(str(path)))


def ensure_onnx_cuda() -> None:
    global _bootstrapped
    if _bootstrapped:
        return
    _bootstrapped = True

    if sys.platform == "win32":
        try:
            import torch

            lib = Path(torch.__file__).resolve().parent / "lib"
            _add_dll_directory(lib)
            site_packages = Path(torch.__file__).resolve().parents[1]
            nvidia_dir = site_packages / "nvidia"
            if nvidia_dir.is_dir():
                for dll_dir in nvidia_dir.glob("*/bin"):
                    _add_dll_directory(dll_dir)
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
