"""Полный E2E-тест GIGAvibe: health → job → video → QR."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8765"
ROOT = Path(__file__).resolve().parent.parent
PHOTO = ROOT / "data" / "test_photo.jpg"
POLL_INTERVAL = 5
MAX_WAIT_SEC = 900  # 15 мин на SVD + первую загрузку модели


def http_json(url: str, method: str = "GET", data: bytes | None = None, content_type: str | None = None) -> dict:
    headers = {}
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def http_bytes(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return resp.read()


def wait_server(max_sec: int = 600) -> dict:
    print(f"[1/6] Ожидание сервера (до {max_sec}s, включая загрузку модели)...")
    deadline = time.time() + max_sec
    last_err = ""
    while time.time() < deadline:
        try:
            health = http_json(f"{BASE}/api/health")
            print(f"      health: {json.dumps(health, ensure_ascii=False)}")
            return health
        except Exception as exc:
            last_err = str(exc)
            time.sleep(5)
    raise RuntimeError(f"Сервер не ответил: {last_err}")


def create_job() -> str:
    print("[2/6] Отправка фото...")
    if not PHOTO.exists():
        raise FileNotFoundError(PHOTO)
    boundary = "----gigavibe-test"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="photo"; filename="test.jpg"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode() + PHOTO.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    result = http_json(
        f"{BASE}/api/jobs",
        method="POST",
        data=body,
        content_type=f"multipart/form-data; boundary={boundary}",
    )
    job_id = result["job_id"]
    print(f"      job_id={job_id}")
    return job_id


def poll_job(job_id: str) -> dict:
    print(f"[3/6] Ожидание генерации (до {MAX_WAIT_SEC}s)...")
    t0 = time.time()
    while time.time() - t0 < MAX_WAIT_SEC:
        data = http_json(f"{BASE}/api/jobs/{job_id}")
        status = data.get("status")
        msg = data.get("message", "")
        elapsed = int(time.time() - t0)
        print(f"      [{elapsed:4d}s] {status}: {msg}")
        if status == "done":
            return data
        if status == "error":
            raise RuntimeError(f"Ошибка задачи: {msg}")
        time.sleep(POLL_INTERVAL)
    raise RuntimeError("Таймаут ожидания генерации")


def verify_outputs(job_id: str, data: dict) -> None:
    print("[4/6] Проверка видео...")
    video_path = data.get("video_path")
    if not video_path:
        raise RuntimeError("Нет video_path в ответе")
    video_bytes = http_bytes(f"{BASE}{video_path}")
    if len(video_bytes) < 10_000:
        raise RuntimeError(f"Видео слишком маленькое: {len(video_bytes)} bytes")
    print(f"      video OK: {len(video_bytes)} bytes")

    print("[5/6] Проверка QR...")
    qr_data = data.get("qr_data_url")
    if not qr_data or not qr_data.startswith("data:image/png;base64,"):
        raise RuntimeError("Нет qr_data_url в ответе")
    b64_len = len(qr_data)
    print(f"      qr_data_url OK: {b64_len} chars")

    qr_path = data.get("qr_path")
    if qr_path:
        qr_bytes = http_bytes(f"{BASE}{qr_path}")
        if len(qr_bytes) < 100:
            raise RuntimeError(f"QR PNG слишком маленький: {len(qr_bytes)}")
        print(f"      qr.png OK: {len(qr_bytes)} bytes")

    download_url = data.get("download_url", "")
    print(f"      download_url: {download_url}")

    out_file = ROOT / "data" / "outputs" / f"{job_id}.mp4"
    if out_file.exists():
        print(f"      файл на диске: {out_file} ({out_file.stat().st_size} bytes)")

    qr_file = ROOT / "data" / "outputs" / f"{job_id}_qr.png"
    if qr_file.exists():
        print(f"      QR на диске: {qr_file} ({qr_file.stat().st_size} bytes)")


def main() -> int:
    print("=== GIGAvibe full test ===\n")
    try:
        health = wait_server()
        if health.get("active_generator") != "SvdGenerator":
            print(f"      ВНИМАНИЕ: генератор {health.get('active_generator')}, ожидался SvdGenerator")
        if not health.get("cuda_available"):
            print("      ВНИМАНИЕ: CUDA недоступна")

        job_id = create_job()
        result = poll_job(job_id)
        verify_outputs(job_id, result)

        print("\n[6/6] ИТОГ: ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")
        return 0
    except Exception as exc:
        print(f"\n[FAIL] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
