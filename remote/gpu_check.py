import os
import sys


def main():
    try:
        import torch
        print("torch", torch.__version__, "cuda_build", torch.version.cuda)
        print("cuda_available", torch.cuda.is_available())
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                print("gpu", i, torch.cuda.get_device_name(i))
    except Exception as exc:
        print("torch ERROR", exc)

    try:
        from app.cuda_bootstrap import ensure_onnx_cuda
        ensure_onnx_cuda()
    except Exception as exc:
        print("cuda_bootstrap ERROR", exc)

    try:
        import onnxruntime as ort
        print("onnxruntime", ort.__version__)
        print("providers", "|".join(ort.get_available_providers()))
    except Exception as exc:
        print("onnxruntime ERROR", exc)


if __name__ == "__main__":
    sys.exit(main())
