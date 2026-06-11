"""Тест отправки на сервер и печати.

Примеры:
    .venv\\Scripts\\python.exe scripts\\test_output_dispatch.py --upload-only
    .venv\\Scripts\\python.exe scripts\\test_output_dispatch.py --print-only --image data\\outputs\\test_flattering.jpg
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import settings
from app.output_dispatch import dispatch_job_output, print_image, upload_output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default="data/outputs/test_flattering.jpg")
    parser.add_argument("--upload-only", action="store_true")
    parser.add_argument("--print-only", action="store_true")
    parser.add_argument("--job-id", default="test-dispatch")
    args = parser.parse_args()

    path = ROOT / args.image
    if not path.exists():
        print(f"Нет файла: {path}")
        return 1

    print(f"upload_enabled={settings.output_upload_enabled} url={settings.output_upload_url}")
    print(f"print_enabled={settings.print_enabled} printer={settings.print_printer_name!r}")

    if args.upload_only:
        upload_output(path, args.job_id, output_filename=path.name)
        print("upload: OK")
        return 0

    if args.print_only:
        print_image(path)
        print("print: OK")
        return 0

    result = dispatch_job_output(
        path,
        args.job_id,
        download_url=f"http://127.0.0.1:{settings.port}/outputs/{path.name}",
        output_filename=path.name,
    )
    print(result)
    print(result.summary_ru())
    ok = (result.upload_ok is not False) and (result.print_ok is not False)
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
