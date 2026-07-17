from pathlib import Path

import pikepdf
import pytest

from app.compressor import PRESETS, compress_pdf


def test_output_is_smaller_and_valid(image_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "out.pdf"
    result = compress_pdf(image_pdf, output, "medium")

    assert result.output_bytes < result.input_bytes
    assert result.images_total == 1
    assert result.images_recompressed == 1
    assert result.saved_percent > 0

    with pikepdf.open(output) as pdf:  # Ausgabe ist ein gültiges PDF
        assert len(pdf.pages) == 1


def test_preset_ordering(image_pdf: Path, tmp_path: Path) -> None:
    sizes = {}
    for name in PRESETS:
        output = tmp_path / f"{name}.pdf"
        sizes[name] = compress_pdf(image_pdf, output, name).output_bytes

    assert sizes["low"] <= sizes["medium"] <= sizes["high"]


def test_image_is_downscaled(image_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "out.pdf"
    compress_pdf(image_pdf, output, "low")  # max. Kante: 96 dpi * 11" = 1056 px

    with pikepdf.open(output) as pdf:
        image = next(iter(pdf.pages[0].get_images().values()))
        assert max(int(image.Width), int(image.Height)) <= PRESETS["low"].max_pixels


def test_pdf_without_images_stays_valid(blank_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "out.pdf"
    result = compress_pdf(blank_pdf, output, "medium")

    assert result.images_total == 0
    with pikepdf.open(output) as pdf:
        assert len(pdf.pages) == 1


def test_unknown_preset_raises(image_pdf: Path, tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        compress_pdf(image_pdf, tmp_path / "out.pdf", "ultra")
