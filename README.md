# PDFCompress

Einfache, lokal laufende Webanwendung zum Komprimieren von PDF-Dateien:
PDF hochladen → komprimierte Version herunterladen. Dateien werden nur im
Arbeitsspeicher bzw. in einem temporären Verzeichnis verarbeitet und nicht gespeichert.

## Voraussetzungen

- [uv](https://docs.astral.sh/uv/) (verwaltet Python 3.14 und das virtuelle Environment automatisch)

## Installation & Start

```powershell
uv sync                                  # erstellt .venv und installiert alle Abhängigkeiten
uv run uvicorn app.main:app --reload     # Entwicklungsserver starten
```

Dann im Browser öffnen: http://127.0.0.1:8000

## Tests

```powershell
uv run pytest
```

## Funktionsweise

- Bilder im PDF werden dekodiert, auf die Ziel-Auflösung der gewählten Stufe
  herunterskaliert und als JPEG neu kodiert – aber nur ersetzt, wenn das Ergebnis
  tatsächlich kleiner ist.
- Nicht sicher verarbeitbare Bilder (Transparenz/SMask, CMYK, CCITT-/JBIG2-Scans,
  JPEG 2000) bleiben unverändert – eine Datei kann dadurch nie kaputtgehen.
- Zusätzlich werden alle Streams rekomprimiert (Objekt-Streams, Flate) und
  XMP-Metadaten sowie Seiten-Thumbnails entfernt.

| Stufe | Ziel-DPI | JPEG-Qualität |
|---|---|---|
| Stark (`low`) | 96 | 40 |
| Ausgewogen (`medium`, Standard) | 120 | 60 |
| Beste Qualität (`high`) | 150 | 75 |

Upload-Limit: 100 MB (änderbar über `MAX_UPLOAD_BYTES` in [app/main.py](app/main.py)).

## Komponenten & Lizenzen

Alle Komponenten sind Open Source und für kommerzielle Nutzung unbedenklich:

| Komponente | Zweck | Lizenz |
|---|---|---|
| [FastAPI](https://fastapi.tiangolo.com/) | Web-Framework | MIT |
| [Uvicorn](https://www.uvicorn.org/) | ASGI-Server | BSD-3 |
| [python-multipart](https://github.com/Kludex/python-multipart) | Upload-Parsing | Apache-2.0 |
| [pikepdf](https://pikepdf.readthedocs.io/) | PDF lesen/schreiben (basiert auf QPDF, Apache-2.0) | MPL-2.0 |
| [Pillow](https://pillow.readthedocs.io/) | Bildverarbeitung | MIT-CMU |
| [Jinja2](https://jinja.palletsprojects.com/) | HTML-Templates | BSD-3 |
| [pytest](https://pytest.org/) | Tests (nur Entwicklung) | MIT |

Das Frontend ist eine einzelne HTML-Seite mit Vanilla-JavaScript ohne externe Abhängigkeiten.
