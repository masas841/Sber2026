"""Клон LivePortrait, venv, веса HF, driving-примеры в assets/driving."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "data" / "liveportrait_download_log.txt"
LP_DIR = ROOT / "vendor" / "LivePortrait"
USE_MAIN = os.environ.get("LIVEPORTRAIT_USE_MAIN_VENV", "").strip().lower() in (
    "1",
    "true",
    "yes",
)
VENV = ROOT / ".venv" if USE_MAIN else ROOT / ".venv-liveportrait"
WEIGHTS = LP_DIR / "pretrained_weights"
DRIVING_OUT = ROOT / "assets" / "driving"
REPO = "https://github.com/KlingTeam/LivePortrait.git"


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


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    log(f"  $ {' '.join(cmd)}")
    r = subprocess.run(
        cmd,
        cwd=cwd or ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if r.stdout:
        for line in r.stdout.splitlines()[-40:]:
            log(f"    {line}")
    if r.returncode != 0:
        if r.stderr:
            log("  --- stderr ---")
            for line in r.stderr.splitlines()[-60:]:
                log(f"    {line}")
        raise SystemExit(r.returncode)


def venv_python() -> Path:
    py = VENV / "Scripts" / "python.exe"
    if not py.exists():
        raise FileNotFoundError(f"Нет {py}")
    return py


def clone_repo() -> None:
    if (LP_DIR / "inference.py").exists():
        log(f"[skip] Репозиторий уже есть: {LP_DIR}")
        return
    LP_DIR.parent.mkdir(parents=True, exist_ok=True)
    log(f"[1/5] git clone -> {LP_DIR}")
    run(["git", "clone", "--depth", "1", REPO, str(LP_DIR)])


def create_venv() -> None:
    py = VENV / "Scripts" / "python.exe"
    if USE_MAIN:
        if not py.exists():
            raise SystemExit("Нет gigavibe\\.venv — сначала install-ai.ps1")
        log(f"[2/5] Используем основной venv: {VENV}")
        return
    if py.exists():
        log(f"[skip] venv: {VENV}")
        return
    log(f"[2/5] python -m venv {VENV}")
    run([sys.executable, "-m", "venv", str(VENV)])


def install_deps() -> None:
    py = venv_python()
    log("[3/5] зависимости LivePortrait")
    if not USE_MAIN:
        run(
            [
                str(py),
                "-m",
                "pip",
                "install",
                "--upgrade",
                "pip",
                "wheel",
                "huggingface_hub",
            ]
        )
        run(
            [
                str(py),
                "-m",
                "pip",
                "install",
                "torch",
                "torchvision",
                "--index-url",
                "https://download.pytorch.org/whl/cu124",
            ]
        )
    else:
        log("  (torch уже в gigavibe .venv)")

    # lmdb==1.4.1 не ставится на Win+Py3.12 (сборка из исходников); wheel есть у 2.x
    log("  lmdb>=2.2 (бинарный wheel для Windows)")
    run([str(py), "-m", "pip", "install", "lmdb>=2.2"])

    base = LP_DIR / "requirements_base.txt"
    extra = LP_DIR / "requirements.txt"
    skip_prefixes = ("lmdb", "numpy")  # numpy 1.26 ломает gigavibe; lmdb — выше
    lines: list[str] = []
    for path in (base, extra):
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith("-r"):
                continue
            if any(line.lower().startswith(p) for p in skip_prefixes):
                continue
            lines.append(line)
    win_req = ROOT / "data" / "_liveportrait_requirements_win.txt"
    win_req.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"  pip install -r {win_req.name} ({len(lines)} пакетов)")
    run([str(py), "-m", "pip", "install", "-r", str(win_req)])


def download_weights() -> None:
    marker = (
        WEIGHTS
        / "liveportrait"
        / "base_models"
        / "appearance_feature_extractor.pth"
    )
    if marker.exists():
        log(f"[skip] Веса: {marker}")
        return

    _load_dotenv()
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if token:
        os.environ["HF_TOKEN"] = token

    py = venv_python()
    log("[4/5] snapshot_download KlingTeam/LivePortrait")
    script = f"""
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="KlingTeam/LivePortrait",
    local_dir={str(WEIGHTS)!r},
    ignore_patterns=["*.git*", "README.md", "docs/**"],
)
print("weights_ok")
"""
    run([str(py), "-c", script.strip()])


def copy_driving_examples() -> None:
    DRIVING_OUT.mkdir(parents=True, exist_ok=True)
    src_dir = LP_DIR / "assets" / "examples" / "driving"
    if not src_dir.is_dir():
        log("[warn] Нет примеров driving в репозитории")
        return
    log("[5/5] Копирую driving .mp4 -> assets/driving/")
    for mp4 in sorted(src_dir.glob("*.mp4")):
        dest = DRIVING_OUT / mp4.name
        if dest.exists():
            continue
        shutil.copy2(mp4, dest)
        log(f"  + {dest.name}")


def main() -> None:
    LOG.write_text("", encoding="utf-8")
    log("=== GIGAvibe LivePortrait install ===")
    try:
        clone_repo()
        create_venv()
        install_deps()
        download_weights()
        copy_driving_examples()
    except SystemExit as e:
        log(f"FAILED code={e.code}")
        raise
    log("")
    log("Готово.")
    log("  .env: GENERATOR_MODE=liveportrait")
    log("  PRELOAD_MODEL_ON_STARTUP=false  (рекомендуется)")
    if USE_MAIN:
        log("  LIVEPORTRAIT_USE_MAIN_VENV=true")
    log("  Запуск: run.ps1")
    log("  Тест: .venv\\Scripts\\python.exe scripts\\test_liveportrait.py")


if __name__ == "__main__":
    main()
