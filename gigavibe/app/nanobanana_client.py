"""HTTP-клиент nanobananaapi.ai (Nano Banana / nana-banana)."""

from __future__ import annotations

import json
import logging
import mimetypes
import time
import uuid
from pathlib import Path
from urllib import error, parse, request

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.nanobananaapi.ai"
DUMMY_CALLBACK_URL = "https://example.com/gigavibe-nanobanana-callback"
DEFAULT_USER_AGENT = "GIGAvibe/1.0 (+https://github.com/gigavibe)"


class NanoBananaApiClient:
    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL) -> None:
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.api_root = f"{self.base_url}/api/v1/nanobanana"

    def _auth_headers(self, *, json_body: bool = False) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": DEFAULT_USER_AGENT,
        }
        if json_body:
            headers["Content-Type"] = "application/json"
        return headers

    def _request_json(self, method: str, url: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = request.Request(url, data=data, headers=self._auth_headers(json_body=True), method=method)
        try:
            with request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"NanoBanana API HTTP {exc.code}: {raw}") from exc

    def submit_generate_v2(
        self,
        prompt: str,
        *,
        image_urls: list[str],
        aspect_ratio: str,
        resolution: str,
        output_format: str = "png",
    ) -> str:
        payload = {
            "prompt": prompt,
            "imageUrls": image_urls,
            "aspectRatio": aspect_ratio,
            "resolution": resolution,
            "outputFormat": output_format,
        }
        result = self._request_json("POST", f"{self.api_root}/generate-2", payload)
        if result.get("code") != 200:
            msg = result.get("message") or result.get("msg") or result
            raise RuntimeError(f"NanoBanana generate-2 failed: {msg}")
        return result["data"]["taskId"]

    def submit_generate_v1(
        self,
        prompt: str,
        *,
        image_urls: list[str],
        image_size: str,
        callback_url: str = DUMMY_CALLBACK_URL,
    ) -> str:
        payload = {
            "prompt": prompt,
            "type": "IMAGETOIAMGE",
            "numImages": 1,
            "imageUrls": image_urls,
            "image_size": image_size,
            "callBackUrl": callback_url,
        }
        result = self._request_json("POST", f"{self.api_root}/generate", payload)
        if result.get("code") != 200:
            msg = result.get("msg") or result
            raise RuntimeError(f"NanoBanana generate failed: {msg}")
        return result["data"]["taskId"]

    def get_task(self, task_id: str) -> dict:
        url = f"{self.api_root}/record-info?{parse.urlencode({'taskId': task_id})}"
        req = request.Request(url, headers=self._auth_headers(), method="GET")
        with request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        data = result.get("data")
        if isinstance(data, dict):
            return data
        return result

    def wait_for_result(
        self,
        task_id: str,
        *,
        poll_sec: float = 3.0,
        timeout_sec: float = 300.0,
    ) -> str:
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            task = self.get_task(task_id)
            flag = task.get("successFlag", -1)
            if flag == 0:
                logger.info("nanobanana task %s: generating…", task_id)
                time.sleep(poll_sec)
                continue
            if flag == 1:
                resp = task.get("response") or {}
                url = resp.get("resultImageUrl")
                if not url:
                    raise RuntimeError("NanoBanana: success без resultImageUrl")
                return url
            err = task.get("errorMessage") or f"successFlag={flag}"
            raise RuntimeError(f"NanoBanana task failed: {err}")
        raise TimeoutError(f"NanoBanana task {task_id} timeout ({timeout_sec}s)")

    @staticmethod
    def download_bytes(url: str) -> bytes:
        req = request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT}, method="GET")
        with request.urlopen(req, timeout=120) as resp:
            return resp.read()


def _is_publicly_reachable(base_url: str) -> bool:
    host = (parse.urlparse(base_url).hostname or "").lower()
    if host in {"", "127.0.0.1", "localhost", "::1"}:
        return False
    if host.startswith("192.168.") or host.startswith("10.") or host.startswith("172."):
        return False
    return True


def publish_source_image_url(source_image: Path) -> str:
    """
    API принимает только публичные imageUrls.
    Если PUBLIC_BASE_URL недоступен из интернета — временный upload на tmpfiles.
    """
    from app.config import settings
    from app.selfie_compress import compress_selfie_jpeg

    jpeg = compress_selfie_jpeg(source_image)

    override = (settings.nanobanana_public_base_url or "").strip()
    public_base = override or settings.effective_public_base_url()
    if _is_publicly_reachable(public_base):
        uploads = settings.data_dir / "outputs" / "nanobanana_uploads"
        uploads.mkdir(parents=True, exist_ok=True)
        dest = uploads / f"{uuid.uuid4().hex}.jpg"
        dest.write_bytes(jpeg)
        return f"{public_base.rstrip('/')}/outputs/{dest.name}"

    logger.info("nanobanana: нет публичного URL — временный upload selfie (%s bytes)", len(jpeg))
    tmp = settings.data_dir / "outputs" / f"_upload_{uuid.uuid4().hex}.jpg"
    tmp.write_bytes(jpeg)
    try:
        return upload_temp_image(tmp)
    finally:
        tmp.unlink(missing_ok=True)


def _multipart_body(fields: dict[str, str], file_field: str, path: Path) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    body = bytearray()
    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.extend(f"{value}\r\n".encode())
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(
        f'Content-Disposition: form-data; name="{file_field}"; filename="{path.name}"\r\n'.encode()
    )
    body.extend(f"Content-Type: {mime}\r\n\r\n".encode())
    body.extend(path.read_bytes())
    body.extend(f"\r\n--{boundary}--\r\n".encode())
    return bytes(body), boundary


def upload_temp_image(path: Path) -> str:
    """Временный хостинг для smoke-тестов и dev без публичного PUBLIC_BASE_URL."""
    errors: list[str] = []

    try:
        body, boundary = _multipart_body({}, "file", path)
        req = request.Request(
            "https://tmpfiles.org/api/v1/upload",
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": DEFAULT_USER_AGENT,
            },
            method="POST",
        )
        with request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        page_url = (payload.get("data") or {}).get("url", "")
        if page_url.startswith("https://tmpfiles.org/"):
            return page_url.replace("https://tmpfiles.org/", "https://tmpfiles.org/dl/", 1)
        errors.append(f"tmpfiles: {payload}")
    except Exception as exc:
        errors.append(f"tmpfiles: {exc}")

    try:
        body, boundary = _multipart_body({}, "file", path)
        req = request.Request(
            "https://0x0.st",
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": DEFAULT_USER_AGENT,
            },
            method="POST",
        )
        with request.urlopen(req, timeout=120) as resp:
            url = resp.read().decode("utf-8").strip()
        if url.startswith("http"):
            return url
        errors.append(f"0x0.st: {url[:200]}")
    except Exception as exc:
        errors.append(f"0x0.st: {exc}")

    raise RuntimeError("Не удалось загрузить selfie для API: " + "; ".join(errors))
