import shutil
from pathlib import Path

ROOT = Path(r"C:\Users\user\gigavibe")


def main():
    try:
        import torch
        print("torch", torch.__version__, "cuda", torch.cuda.is_available(),
              "bf16", torch.cuda.is_bf16_supported() if torch.cuda.is_available() else False)
    except Exception as e:
        print("torch ERROR", e)

    try:
        import diffusers
        print("diffusers", diffusers.__version__)
        from diffusers import LTXImageToVideoPipeline  # noqa
        print("LTXImageToVideoPipeline OK")
    except Exception as e:
        print("diffusers ERROR", e)

    try:
        import transformers
        print("transformers", transformers.__version__)
    except Exception as e:
        print("transformers ERROR", e)

    model_dir = ROOT / "models" / "LTX-Video"
    idx = model_dir / "model_index.json"
    print("model_dir_exists", model_dir.exists(), "model_index", idx.exists())
    if model_dir.exists():
        total = sum(p.stat().st_size for p in model_dir.rglob("*") if p.is_file())
        print("model_size_GB", round(total / (1024**3), 2))

    usage = shutil.disk_usage(str(ROOT))
    print("disk_free_GB", round(usage.free / (1024**3), 1))


if __name__ == "__main__":
    main()
