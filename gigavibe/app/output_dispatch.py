"""Отправка готового результата на внешний сервер и печать на принтере (Windows)."""

from __future__ import annotations

import logging
import mimetypes
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageOps

from app.config import settings
from app.qr_util import build_download_url
from app.upload_client import upload_output_with_resume
from app.upload_queue import PendingUpload, dequeue_pending, enqueue_pending

if TYPE_CHECKING:
    from app.guest_profile import GuestProfile

logger = logging.getLogger(__name__)


@dataclass
class DispatchResult:
    upload_ok: bool | None = None
    upload_error: str | None = None
    print_ok: bool | None = None
    print_error: str | None = None
    upload_sec: float | None = None
    print_sec: float | None = None
    public_url: str | None = None

    def summary_ru(self) -> str:
        parts: list[str] = []
        if self.upload_ok is True:
            parts.append("отправлено на сервер")
        elif self.upload_ok is False:
            parts.append(f"сервер: {self.upload_error or 'ошибка'}")
        if self.print_ok is True:
            parts.append("отправлено на печать")
        elif self.print_ok is False:
            parts.append(f"печать: {self.print_error or 'ошибка'}")
        return ", ".join(parts) if parts else ""


def _default_printer_name() -> str | None:
    if sys.platform != "win32":
        return None
    script = (
        "(Get-CimInstance Win32_Printer | Where-Object { $_.Default -eq $true } "
        "| Select-Object -ExpandProperty Name -First 1)"
    )
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    name = (proc.stdout or "").strip()
    return name or None


def _photo_print_path(output_path: Path) -> Path:
    width_px = max(1, round(settings.print_width_mm / 25.4 * settings.print_dpi))
    height_px = max(1, round(settings.print_height_mm / 25.4 * settings.print_dpi))

    with Image.open(output_path) as image:
        prepared = ImageOps.fit(
            image.convert("RGB"),
            (width_px, height_px),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
        tmp = tempfile.NamedTemporaryFile(
            prefix="gigavibe-print-",
            suffix=".jpg",
            delete=False,
        )
        tmp_path = Path(tmp.name)
        tmp.close()
        prepared.save(
            tmp_path,
            "JPEG",
            quality=95,
            subsampling=0,
            dpi=(settings.print_dpi, settings.print_dpi),
        )
        return tmp_path


def _print_image_gdi(output_path: Path, printer: str) -> None:
    paper_width = max(1, round(settings.print_width_mm / 25.4 * 100))
    paper_height = max(1, round(settings.print_height_mm / 25.4 * 100))
    script = r"""
param(
    [Parameter(Mandatory = $true)][string]$ImagePath,
    [Parameter(Mandatory = $true)][string]$PrinterName,
    [Parameter(Mandatory = $true)][int]$PaperWidth,
    [Parameter(Mandatory = $true)][int]$PaperHeight
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$doc = New-Object System.Drawing.Printing.PrintDocument
$doc.PrinterSettings.PrinterName = $PrinterName
$doc.DocumentName = "GIGAvibe 10x15 photo"
$doc.OriginAtMargins = $false
$doc.DefaultPageSettings.Landscape = $false
$doc.DefaultPageSettings.Margins = New-Object System.Drawing.Printing.Margins(0, 0, 0, 0)
$doc.DefaultPageSettings.PaperSize = New-Object System.Drawing.Printing.PaperSize("10x15 borderless", $PaperWidth, $PaperHeight)

$image = [System.Drawing.Image]::FromFile($ImagePath)
$handler = [System.Drawing.Printing.PrintPageEventHandler]{
    param($sender, $event)
    $event.Graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $event.Graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $event.Graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
    $event.Graphics.DrawImage($image, $event.PageBounds)
    $event.HasMorePages = $false
}
$doc.add_PrintPage($handler)
try {
    $doc.Print()
} finally {
    $doc.remove_PrintPage($handler)
    $image.Dispose()
    $doc.Dispose()
}
"""
    script_file = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix="gigavibe-print-",
        suffix=".ps1",
        delete=False,
    )
    script_path = Path(script_file.name)
    try:
        script_file.write(script)
        script_file.close()
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
                "-ImagePath",
                str(output_path),
                "-PrinterName",
                printer,
                "-PaperWidth",
                str(paper_width),
                "-PaperHeight",
                str(paper_height),
            ],
            capture_output=True,
            timeout=settings.print_timeout_sec,
            check=False,
        )
    finally:
        script_file.close()
        script_path.unlink(missing_ok=True)

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(err or f"PrintDocument exit {proc.returncode}")


def print_image(output_path: Path, printer_name: str | None = None) -> None:
    if sys.platform != "win32":
        raise RuntimeError("Печать поддерживается только на Windows")

    path = output_path.resolve()
    if not path.exists():
        raise RuntimeError(f"Файл не найден: {path}")

    ext = path.suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
        raise RuntimeError(f"Печать не поддерживается для {ext}")

    printer = (printer_name or settings.print_printer_name or "").strip()
    if not printer:
        printer = _default_printer_name()
    if not printer:
        raise RuntimeError("Принтер по умолчанию не найден")

    print_path = _photo_print_path(path)
    try:
        _print_image_gdi(print_path, printer)
    finally:
        print_path.unlink(missing_ok=True)
    logger.info(
        "print: file=%s printer=%s paper=%.1fx%.1fmm dpi=%s",
        path.name,
        printer,
        settings.print_width_mm,
        settings.print_height_mm,
        settings.print_dpi,
    )


def should_print_file(path: Path) -> bool:
    if not settings.print_enabled:
        return False
    if not settings.print_only_images:
        return True
    return path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def should_upload_file() -> bool:
    return bool(settings.output_upload_enabled and (settings.output_upload_url or "").strip())


def upload_output(
    output_path: Path,
    job_id: str,
    *,
    guest_profile: "GuestProfile | None" = None,
    download_url: str | None = None,
    output_filename: str | None = None,
) -> str | None:
    """Upload с докачкой; при сбое ставит задачу в локальную очередь."""
    filename = output_filename or output_path.name
    qr_url = download_url or build_download_url(filename)

    pending = PendingUpload(
        job_id=job_id,
        output_path=str(output_path.resolve()),
        output_filename=filename,
        download_url=qr_url,
    )
    enqueue_pending(pending)

    upload_id: str | None = None
    try:
        public_url, upload_id, received = upload_output_with_resume(
            output_path,
            job_id,
            guest_profile=guest_profile,
            download_url=qr_url,
            output_filename=filename,
        )
        dequeue_pending(job_id)
        return public_url or build_download_url(filename)
    except Exception as exc:
        pending.last_error = str(exc)
        if upload_id:
            pending.upload_id = upload_id
        enqueue_pending(pending)
        raise


def dispatch_job_output(
    output_path: Path,
    job_id: str,
    *,
    guest_profile: "GuestProfile | None" = None,
    download_url: str | None = None,
    output_filename: str | None = None,
) -> DispatchResult:
    result = DispatchResult()
    do_upload = should_upload_file()
    do_print = should_print_file(output_path)
    filename = output_filename or output_path.name
    qr_fallback = download_url or build_download_url(filename)

    if do_upload and settings.print_after_upload and do_print:
        order = ("upload", "print")
    elif do_print and not settings.print_after_upload and do_upload:
        order = ("print", "upload")
    else:
        order = tuple(
            step
            for step, enabled in (("upload", do_upload), ("print", do_print))
            if enabled
        )

    for step in order:
        if step == "upload":
            t0 = time.perf_counter()
            try:
                result.public_url = upload_output(
                    output_path,
                    job_id,
                    guest_profile=guest_profile,
                    download_url=qr_fallback,
                    output_filename=filename,
                )
                result.upload_ok = True
            except Exception as exc:
                result.upload_ok = False
                result.upload_error = str(exc)
                logger.warning("output_upload failed job=%s: %s", job_id, exc)
            result.upload_sec = time.perf_counter() - t0
        elif step == "print":
            t0 = time.perf_counter()
            try:
                print_image(output_path)
                result.print_ok = True
            except Exception as exc:
                result.print_ok = False
                result.print_error = str(exc)
                logger.warning("print failed job=%s: %s", job_id, exc)
            result.print_sec = time.perf_counter() - t0

    if result.public_url is None and do_upload:
        result.public_url = qr_fallback

    return result


def dispatch_status_dict(result: DispatchResult) -> dict:
    payload: dict = {}
    if result.upload_ok is not None:
        payload["upload_ok"] = result.upload_ok
        if result.upload_error:
            payload["upload_error"] = result.upload_error
    if result.print_ok is not None:
        payload["print_ok"] = result.print_ok
        if result.print_error:
            payload["print_error"] = result.print_error
    if result.upload_sec is not None:
        payload["upload_sec"] = round(result.upload_sec, 2)
    if result.print_sec is not None:
        payload["print_sec"] = round(result.print_sec, 2)
    if result.public_url:
        payload["public_url"] = result.public_url
    return payload
