from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main
from app.main import app as fastapi_app

client = TestClient(fastapi_app)


def test_index_page() -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "PDFCompress" in resp.text


def test_compress_roundtrip(image_pdf: Path) -> None:
    resp = client.post(
        "/compress",
        files={"file": ("mein dokument.pdf", image_pdf.read_bytes(), "application/pdf")},
        data={"preset": "medium"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")
    assert "mein dokument_komprimiert.pdf" in resp.headers["content-disposition"]

    original = int(resp.headers["x-original-size"])
    compressed = int(resp.headers["x-compressed-size"])
    assert compressed == len(resp.content)
    assert compressed < original


def test_rejects_non_pdf() -> None:
    resp = client.post(
        "/compress",
        files={"file": ("notes.txt", b"kein pdf inhalt", "text/plain")},
    )
    assert resp.status_code == 400


def test_rejects_empty_file() -> None:
    resp = client.post("/compress", files={"file": ("leer.pdf", b"", "application/pdf")})
    assert resp.status_code == 400


def test_rejects_unknown_preset(image_pdf: Path) -> None:
    resp = client.post(
        "/compress",
        files={"file": ("a.pdf", image_pdf.read_bytes(), "application/pdf")},
        data={"preset": "ultra"},
    )
    assert resp.status_code == 400


def test_rejects_oversized_file(monkeypatch: pytest.MonkeyPatch, image_pdf: Path) -> None:
    monkeypatch.setattr(app.main, "MAX_UPLOAD_BYTES", 1024)
    resp = client.post(
        "/compress",
        files={"file": ("gross.pdf", image_pdf.read_bytes(), "application/pdf")},
    )
    assert resp.status_code == 413


def test_rejects_corrupt_pdf() -> None:
    resp = client.post(
        "/compress",
        files={"file": ("kaputt.pdf", b"%PDF-1.7 nur ein header, kein inhalt", "application/pdf")},
    )
    assert resp.status_code == 400
