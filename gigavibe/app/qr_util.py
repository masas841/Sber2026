from pathlib import Path

import qrcode
from qrcode.constants import ERROR_CORRECT_M

from app.config import settings


def effective_qr_base_url() -> str:
    override = (settings.qr_public_base_url or "").strip()
    if override:
        return override.rstrip("/")
    return settings.effective_public_base_url().rstrip("/")


def build_download_url(output_filename: str, *, public_url: str | None = None) -> str:
    if public_url:
        return public_url.rstrip("/")
    base = effective_qr_base_url()
    safe = Path(output_filename).name
    return f"{base}/p/{safe}"


def qr_output_path(job_id: str) -> Path:
    return settings.data_dir / "outputs" / f"{job_id}_qr.png"


def save_job_qr(
    job_id: str,
    output_filename: str,
    *,
    download_url: str | None = None,
) -> Path:
    url = download_url or build_download_url(output_filename)
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    path = qr_output_path(job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path
