"""Serve kiosk install packages from ROOT/dist at /install."""

from __future__ import annotations

import html
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

_PACKAGE_SUFFIX = ".zip"


def register_install_routes(app: FastAPI, root: Path, service_label: str) -> None:
    dist_dir = root / "dist"
    install_doc = root / "install" / "README-INSTALL.md"

    @app.get("/install", response_class=HTMLResponse, include_in_schema=False)
    @app.get("/install/", response_class=HTMLResponse, include_in_schema=False)
    def install_index() -> str:
        packages: list[Path] = []
        if dist_dir.is_dir():
            packages = sorted(
                [p for p in dist_dir.iterdir() if p.is_file() and p.name.endswith(_PACKAGE_SUFFIX) and "-kiosk" in p.name],
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
        rows: list[str] = []
        for pkg in packages:
            mb = pkg.stat().st_size / (1024 * 1024)
            name = html.escape(pkg.name)
            rows.append(f"<li><a href=\"/install/{name}\">{name}</a> ({mb:.1f} MB)</li>")
        doc_block = ""
        if install_doc.is_file():
            doc_block = "<p><a href=\"/install/README-INSTALL.md\">README-INSTALL.md</a></p>"
        list_html = "\n".join(rows) if rows else (
            "<li>Пакеты не найдены в dist/. Соберите: <code>scripts\\build_install_package.ps1</code></li>"
        )
        title = html.escape(service_label)
        return (
            f"<!DOCTYPE html><html lang=\"ru\"><head><meta charset=\"utf-8\">"
            f"<title>{title} — install</title></head><body>"
            f"<h1>{title} — установка</h1>{doc_block}<ul>{list_html}</ul></body></html>"
        )

    @app.get("/install/README-INSTALL.md", include_in_schema=False)
    def install_readme() -> FileResponse:
        if not install_doc.is_file():
            raise HTTPException(status_code=404, detail="README-INSTALL.md not found")
        return FileResponse(install_doc, media_type="text/markdown; charset=utf-8")

    @app.get("/install/{filename}", include_in_schema=False)
    def install_download(filename: str) -> FileResponse:
        if "/" in filename or "\\" in filename or filename != Path(filename).name:
            raise HTTPException(status_code=400, detail="invalid filename")
        if not filename.endswith(_PACKAGE_SUFFIX) or "-kiosk" not in filename:
            raise HTTPException(status_code=404, detail="package not found")
        path = dist_dir / filename
        if not path.is_file():
            raise HTTPException(status_code=404, detail="package not found")
        return FileResponse(path, media_type="application/zip", filename=filename)
