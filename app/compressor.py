"""PDF-Kompression mit pikepdf + Pillow.

Strategie: Bilder im PDF werden dekodiert, bei Bedarf herunterskaliert und als
JPEG neu kodiert. Ein Bild wird nur ersetzt, wenn das Ergebnis kleiner ist.
Alles, was nicht sicher verarbeitet werden kann (Transparenz, CMYK,
CCITT/JBIG2/JPX-kodierte Scans, exotische Farbräume), bleibt unverändert.
Zusätzlich werden alle Streams rekomprimiert und Metadaten-Ballast entfernt.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from pathlib import Path

import pikepdf
from PIL import Image

logger = logging.getLogger(__name__)

# Heuristik: Da die tatsächliche Platzierungsgröße eines Bildes auf der Seite
# ohne Content-Stream-Analyse nicht bekannt ist, wird angenommen, dass ein Bild
# höchstens eine ganze Seite (lange Kante ~11 Zoll) füllt. Die lange Bildkante
# wird entsprechend auf target_dpi * 11 Pixel begrenzt.
ASSUMED_PAGE_INCHES = 11.0

# Bilder mit diesen Filtern sind bereits hocheffizient komprimiert
# (Scans/JPEG2000) und werden nicht angefasst.
SKIP_FILTERS = {"/CCITTFaxDecode", "/JBIG2Decode", "/JPXDecode"}


@dataclass(frozen=True)
class Preset:
    name: str
    target_dpi: int
    jpeg_quality: int

    @property
    def max_pixels(self) -> int:
        return int(self.target_dpi * ASSUMED_PAGE_INCHES)


PRESETS: dict[str, Preset] = {
    "low": Preset("low", target_dpi=96, jpeg_quality=40),
    "medium": Preset("medium", target_dpi=120, jpeg_quality=60),
    "high": Preset("high", target_dpi=150, jpeg_quality=75),
}


@dataclass
class CompressionResult:
    input_bytes: int
    output_bytes: int
    images_total: int
    images_recompressed: int

    @property
    def saved_percent(self) -> float:
        if self.input_bytes == 0:
            return 0.0
        return (1 - self.output_bytes / self.input_bytes) * 100


def _stream_filters(obj: pikepdf.Object) -> set[str]:
    filt = obj.get("/Filter")
    if filt is None:
        return set()
    if isinstance(filt, pikepdf.Name):
        return {str(filt)}
    return {str(f) for f in filt}


def _is_safe_to_recompress(obj: pikepdf.Object) -> bool:
    if obj.get("/SMask") is not None or obj.get("/Mask") is not None:
        return False  # Transparenz würde beim JPEG-Rewrite verloren gehen
    if bool(obj.get("/ImageMask", False)):
        return False
    if _stream_filters(obj) & SKIP_FILTERS:
        return False
    return True


def _recompress_image(obj: pikepdf.Object, preset: Preset) -> bool:
    """Versucht, ein einzelnes Bild-XObject neu zu komprimieren.

    Gibt True zurück, wenn das Bild ersetzt wurde.
    """
    if not _is_safe_to_recompress(obj):
        return False

    pil = pikepdf.PdfImage(obj).as_pil_image()

    if pil.mode == "P":
        pil = pil.convert("RGB")
    if pil.mode not in ("RGB", "L"):
        return False  # CMYK, Transparenz, 1-Bit usw. unverändert lassen

    if max(pil.size) > preset.max_pixels:
        scale = preset.max_pixels / max(pil.size)
        new_size = (max(1, round(pil.width * scale)), max(1, round(pil.height * scale)))
        pil = pil.resize(new_size, Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    pil.save(buf, format="JPEG", quality=preset.jpeg_quality, optimize=True)
    jpeg = buf.getvalue()

    if len(jpeg) >= len(obj.read_raw_bytes()):
        return False  # nur ersetzen, wenn tatsächlich kleiner

    obj.write(jpeg, filter=pikepdf.Name("/DCTDecode"))
    obj.Width, obj.Height = pil.width, pil.height
    obj.ColorSpace = pikepdf.Name("/DeviceRGB" if pil.mode == "RGB" else "/DeviceGray")
    obj.BitsPerComponent = 8
    for stale in ("/DecodeParms", "/Decode", "/Intent"):
        if stale in obj:
            del obj[stale]
    return True


def _strip_metadata(pdf: pikepdf.Pdf) -> None:
    if "/Metadata" in pdf.Root:
        del pdf.Root["/Metadata"]
    for page in pdf.pages:
        if "/Thumb" in page.obj:
            del page.obj["/Thumb"]


def compress_pdf(input_path: Path, output_path: Path, preset_name: str = "medium") -> CompressionResult:
    """Komprimiert ein PDF. Wirft pikepdf.PdfError bei kaputten und
    pikepdf.PasswordError bei verschlüsselten Dateien."""
    preset = PRESETS[preset_name]
    images_total = 0
    images_recompressed = 0

    with pikepdf.open(input_path) as pdf:
        seen: set[tuple[int, int]] = set()
        for page in pdf.pages:
            for _, obj in page.get_images().items():
                if obj.objgen in seen:
                    continue  # von mehreren Seiten geteilte Bilder nur einmal
                seen.add(obj.objgen)
                images_total += 1
                try:
                    if _recompress_image(obj, preset):
                        images_recompressed += 1
                except Exception:
                    logger.warning("Bild %s übersprungen", obj.objgen, exc_info=True)

        _strip_metadata(pdf)

        pdf.save(
            output_path,
            compress_streams=True,
            recompress_flate=True,
            object_stream_mode=pikepdf.ObjectStreamMode.generate,
        )

    return CompressionResult(
        input_bytes=input_path.stat().st_size,
        output_bytes=output_path.stat().st_size,
        images_total=images_total,
        images_recompressed=images_recompressed,
    )
