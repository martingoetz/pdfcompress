"""FastAPI-Anwendung: PDF hochladen, komprimierte Version herunterladen."""

from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path

import pikepdf
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.compressor import PRESETS, compress_pdf

MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 MB
_CHUNK = 1024 * 1024

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="PDFCompress")
app.mount("/static", StaticFiles(directory=BASE_DIR.parent / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")


def _safe_download_name(original: str | None) -> str:
    stem = Path(original or "dokument").stem
    stem = re.sub(r"[^\w\- ]", "_", stem, flags=re.UNICODE).strip() or "dokument"
    return f"{stem}_komprimiert.pdf"


@app.post("/compress")
def compress(file: UploadFile = File(...), preset: str = Form("medium")) -> Response:
    if preset not in PRESETS:
        raise HTTPException(status_code=400, detail="Unbekannte Qualitätsstufe.")

    with tempfile.TemporaryDirectory(prefix="pdfcompress-") as tmp:
        input_path = Path(tmp) / "input.pdf"
        output_path = Path(tmp) / "output.pdf"

        size = 0
        with input_path.open("wb") as f:
            while chunk := file.file.read(_CHUNK):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Datei zu groß (Limit: {MAX_UPLOAD_BYTES // (1024 * 1024)} MB).",
                    )
                f.write(chunk)

        if size == 0:
            raise HTTPException(status_code=400, detail="Leere Datei.")
        with input_path.open("rb") as f:
            if not f.read(5).startswith(b"%PDF"):
                raise HTTPException(status_code=400, detail="Die Datei ist kein PDF.")

        try:
            result = compress_pdf(input_path, output_path, preset)
        except pikepdf.PasswordError:
            raise HTTPException(status_code=400, detail="Das PDF ist passwortgeschützt.")
        except pikepdf.PdfError:
            raise HTTPException(status_code=400, detail="Das PDF ist beschädigt oder ungültig.")

        # Wenn die "komprimierte" Datei größer wäre, Original zurückgeben.
        best = output_path if result.output_bytes < result.input_bytes else input_path
        content = best.read_bytes()

    filename = _safe_download_name(file.filename)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Original-Size": str(result.input_bytes),
            "X-Compressed-Size": str(len(content)),
        },
    )
