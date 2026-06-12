from __future__ import annotations

import app.cuda_bootstrap  # noqa: F401 - imports torch and registers CUDA DLL paths first.
import onnxruntime as ort

from app.generators.ref_video import INSIGHTFACE_ROOT, _onnx_providers


def main() -> int:
    det_model = INSIGHTFACE_ROOT / "models" / "buffalo_l" / "det_10g.onnx"
    if not det_model.exists():
        print(f"ONNX CUDA check skipped: model not found: {det_model}")
        return 1

    providers = _onnx_providers(0)
    session = ort.InferenceSession(str(det_model), providers=providers)
    active_provider = session.get_providers()[0]
    print("ONNX requested providers:", providers)
    print("ONNX active provider:", active_provider)
    return 0 if active_provider == "CUDAExecutionProvider" else 2


if __name__ == "__main__":
    raise SystemExit(main())
