"""Скачать LTX-Video в gigavibe/models/ (обход битого HF-кэша на Windows)."""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "data" / "ltx_download_log.txt"
OUT = ROOT / "models" / "LTX-Video"
# Ориентир для процента (полный репозиторий ~15–25 GB)
ESTIMATED_GB = 22.0
sys.path.insert(0, str(ROOT))


def _load_dotenv() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return

    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"'))


def log(msg: str) -> None:
    print(msg, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


def _folder_stats() -> tuple[int, int]:
    if not OUT.exists():
        return 0, 0
    total = 0
    count = 0
    for path in OUT.rglob("*"):
        if path.is_file():
            total += path.stat().st_size
            count += 1
    return total, count


def _fmt_gb(num_bytes: int) -> str:
    return f"{num_bytes / (1024**3):.2f}"


def _fmt_speed(num_bytes_per_sec: float) -> str:
    if num_bytes_per_sec >= 1024**2:
        return f"{num_bytes_per_sec / (1024**2):.1f} MB/s"
    if num_bytes_per_sec >= 1024:
        return f"{num_bytes_per_sec / 1024:.1f} KB/s"
    return f"{num_bytes_per_sec:.0f} B/s"


def _progress_monitor(stop: threading.Event) -> None:
    last_size = 0
    last_time = time.time()
    last_log_time = 0.0

    while not stop.is_set():
        size, nfiles = _folder_stats()
        now = time.time()
        dt = max(now - last_time, 0.001)
        speed = (size - last_size) / dt
        last_size = size
        last_time = now

        pct = min(100.0, (size / (ESTIMATED_GB * 1024**3)) * 100) if size else 0.0
        line = (
            f"\r  Скачано: {_fmt_gb(size)} / ~{ESTIMATED_GB:.0f} GB ({pct:.0f}%)"
            f"  |  Скорость: {_fmt_speed(speed)}"
            f"  |  Файлов: {nfiles}    "
        )
        print(line, end="", flush=True)

        if now - last_log_time >= 30:
            log(
                f"[прогресс] {_fmt_gb(size)} GB, {_fmt_speed(speed)}, файлов: {nfiles}"
            )
            last_log_time = now

        stop.wait(1.0)

    print(flush=True)


def _run_download(token: str | None, error_box: list) -> None:
    try:
        from huggingface_hub import snapshot_download

        os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"
        snapshot_download(
            repo_id="Lightricks/LTX-Video",
            local_dir=str(OUT),
            token=token,
            max_workers=4,
        )
    except Exception as exc:
        error_box.append(exc)


def main() -> int:
    _load_dotenv()
    LOG.write_text("", encoding="utf-8")

    log("=" * 50)
    log("GIGAvibe — загрузка LTX-Video")
    log(f"Папка: {OUT}")
    log(f"Ожидаемый размер: ~{ESTIMATED_GB:.0f} GB")
    log("=" * 50)

    token = os.environ.get("HF_TOKEN")
    if token:
        log("HF_TOKEN: OK (загрузка с авторизацией)")
    else:
        log("HF_TOKEN: не задан (будет медленнее)")

    log("")
    log("Прогресс обновляется каждую секунду в этой строке:")
    log("")

    stop = threading.Event()
    monitor = threading.Thread(target=_progress_monitor, args=(stop,), daemon=True)
    errors: list[Exception] = []

    monitor.start()
    worker = threading.Thread(target=_run_download, args=(token, errors), daemon=True)
    worker.start()
    worker.join()
    stop.set()
    monitor.join(timeout=2)

    if errors:
        log(f"ERROR: {errors[0]}")
        return 1

    final_size, final_files = _folder_stats()
    log("")
    log(f"Готово: {_fmt_gb(final_size)} GB, файлов: {final_files}")
    log(f"Done: {OUT / 'model_index.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
