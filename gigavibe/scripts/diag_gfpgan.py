"""Диагностика API GFPGAN/facexlib на FARM — для инлайн-restore.

Печатает версии и доступные атрибуты/сигнатуры FaceRestoreHelper,
чтобы реализовать энханс по УЖЕ выровненному 512-кропу без RetinaFace/parsenet.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    from app.face_restore import _get_restorer, _patch_torchvision_for_basicsr

    _patch_torchvision_for_basicsr()

    import facexlib
    import gfpgan

    print("gfpgan:", getattr(gfpgan, "__version__", "?"))
    print("facexlib:", getattr(facexlib, "__version__", "?"))

    r = _get_restorer()
    print("device:", r.device)
    print("has .gfpgan:", hasattr(r, "gfpgan"))
    print("gfpgan.forward sig:", str(inspect.signature(r.gfpgan.forward)))

    fh = r.face_helper
    print("face_helper type:", type(fh).__name__)
    for attr in (
        "all_landmarks_5",
        "cropped_faces",
        "restored_faces",
        "affine_matrices",
        "inverse_affine_matrices",
        "face_template",
        "face_size",
        "upscale_factor",
        "pad_input_imgs",
        "input_img",
    ):
        print(f"  has {attr}:", hasattr(fh, attr))

    for meth in ("clean_all", "read_image", "align_warp_face",
                 "add_restored_face", "get_inverse_affine",
                 "paste_faces_to_input_image"):
        fn = getattr(fh, meth, None)
        if fn is None:
            print(f"  method {meth}: MISSING")
        else:
            print(f"  method {meth}{inspect.signature(fn)}")

    # img2tensor/tensor2img доступность
    try:
        from basicsr.utils import img2tensor, tensor2img  # noqa: F401
        print("basicsr img2tensor/tensor2img: ok")
    except Exception as exc:
        print("basicsr utils import FAIL:", exc)


if __name__ == "__main__":
    main()
