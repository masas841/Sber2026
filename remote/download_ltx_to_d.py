"""Скачать LTX-Video на диск D: (на FARM C: почти заполнен).

Запуск на FARM:
    .venv\\Scripts\\python.exe remote\\download_ltx_to_d.py
Целевая папка: D:\\gigavibe-models\\LTX-Video
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path

TARGET = Path(r"D:\gigavibe-models\LTX-Video")
HF_CACHE = Path(r"D:\gigavibe-models\hf-cache")
ESTIMATED_GB = 22.0

os.environ["HF_HOME"] = str(HF_CACHE)
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"


def _stats():
    if not TARGET.exists():
        return 0, 0
    total = 0
    count = 0
    for p in TARGET.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
            count += 1
    return total, count


def _gb(n):
    return f"{n / (1024**3):.2f}"


def _monitor(stop):
    last = 0
    lastt = time.time()
    while not stop.is_set():
        size, nfiles = _stats()
        now = time.time()
        dt = max(now - lastt, 0.001)
        speed = (size - last) / dt / (1024**2)
        last = size
        lastt = now
        pct = min(100, size / (ESTIMATED_GB * 1024**3) * 100) if size else 0
        print(f"  {_gb(size)} / ~{ESTIMATED_GB:.0f} GB ({pct:.0f}%)  {speed:.1f} MB/s  files={nfiles}", flush=True)
        stop.wait(10.0)


def _download(box):
    try:
        from huggingface_hub import snapshot_download

        TARGET.mkdir(parents=True, exist_ok=True)
        # Только diffusers-формат (2B): подпапки + model_index.json.
        # Корневые ltx-video-*.safetensors и 13B-чекпойнты НЕ качаем.
        snapshot_download(
            repo_id="Lightricks/LTX-Video",
            local_dir=str(TARGET),
            token=os.environ.get("HF_TOKEN"),
            max_workers=4,
            allow_patterns=[
                "model_index.json",
                "scheduler/*",
                "text_encoder/*",
                "tokenizer/*",
                "transformer/*",
                "vae/*",
            ],
        )
    except Exception as exc:
        box.append(exc)


def main():
    print("=" * 50, flush=True)
    print(f"LTX-Video -> {TARGET}", flush=True)
    print(f"HF cache  -> {HF_CACHE}", flush=True)
    print("=" * 50, flush=True)

    stop = threading.Event()
    box = []
    mon = threading.Thread(target=_monitor, args=(stop,), daemon=True)
    wrk = threading.Thread(target=_download, args=(box,), daemon=True)
    mon.start()
    wrk.start()
    wrk.join()
    stop.set()
    mon.join(timeout=2)

    if box:
        print(f"ERROR: {box[0]}", flush=True)
        return 1
    size, nfiles = _stats()
    print(f"DONE: {_gb(size)} GB, files={nfiles}", flush=True)
    print(f"model_index: {(TARGET / 'model_index.json').exists()}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
