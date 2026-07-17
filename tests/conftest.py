"""Test-Helfer: erzeugt Test-PDFs zur Laufzeit (keine Binärdateien im Repo)."""

from __future__ import annotations

import io
import os
from pathlib import Path

import pikepdf
import pytest
from PIL import Image


def _photo_like_image(width: int = 1400, height: int = 1100) -> Image.Image:
    """Verrauschter Farbverlauf: lässt sich per Flate kaum, per JPEG gut komprimieren."""
    gradient = Image.linear_gradient("L").resize((width, height))
    rgb = Image.merge(
        "RGB",
        (
            gradient,
            gradient.transpose(Image.Transpose.FLIP_TOP_BOTTOM),
            gradient.transpose(Image.Transpose.FLIP_LEFT_RIGHT),
        ),
    )
    noise = Image.frombytes("RGB", (width, height), os.urandom(width * height * 3))
    return Image.blend(rgb, noise, 0.5)


def make_pdf_with_image(path: Path, width: int = 1400, height: int = 1100) -> None:
    img = _photo_like_image(width, height)
    pdf = pikepdf.new()
    page = pdf.add_blank_page(page_size=(612, 792))

    image = pikepdf.Stream(pdf, img.tobytes())
    image.Type = pikepdf.Name("/XObject")
    image.Subtype = pikepdf.Name("/Image")
    image.Width = width
    image.Height = height
    image.ColorSpace = pikepdf.Name("/DeviceRGB")
    image.BitsPerComponent = 8

    page.obj["/Resources"] = pikepdf.Dictionary(
        XObject=pikepdf.Dictionary(Im0=image)
    )
    page.obj["/Contents"] = pikepdf.Stream(pdf, b"q 612 0 0 792 0 0 cm /Im0 Do Q")
    pdf.save(path)


def make_blank_pdf(path: Path) -> None:
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(612, 792))
    pdf.save(path)


@pytest.fixture
def image_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "input.pdf"
    make_pdf_with_image(path)
    return path


@pytest.fixture
def blank_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "blank.pdf"
    make_blank_pdf(path)
    return path
