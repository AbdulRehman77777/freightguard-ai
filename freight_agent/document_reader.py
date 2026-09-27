"""Safe text extraction for supported freight document formats."""

from __future__ import annotations

from pathlib import Path

import pymupdf

from .exceptions import DocumentReadError

SUPPORTED_EXTENSIONS = {".txt", ".pdf"}


def _require_text(text: str, source: str) -> str:
    if not text.strip():
        raise DocumentReadError(
            f"No readable text was found in {source}. Scanned PDFs require OCR, which is not enabled."
        )
    return text.strip()


def read_txt(path: Path) -> str:
    try:
        return _require_text(path.read_text(encoding="utf-8"), str(path))
    except UnicodeDecodeError as exc:
        raise DocumentReadError(f"Text file is not valid UTF-8: {path}") from exc
    except OSError as exc:
        raise DocumentReadError(f"Unable to read text file: {path}") from exc


def read_pdf(path: Path) -> str:
    try:
        with pymupdf.open(path) as pdf:
            pages = [page.get_text("text", sort=True).strip() for page in pdf]
    except (OSError, RuntimeError, ValueError) as exc:
        raise DocumentReadError(f"Unable to read PDF: {path}") from exc
    return _require_text("\n\n".join(page for page in pages if page), str(path))


def read_document(path: str | Path) -> str:
    document_path = Path(path)
    if not document_path.exists():
        raise DocumentReadError(f"Input file does not exist: {document_path}")
    if not document_path.is_file():
        raise DocumentReadError(f"Input path is not a file: {document_path}")
    suffix = document_path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise DocumentReadError(
            f"Unsupported file type '{suffix or '(none)'}'. Supported types: .txt, .pdf."
        )
    return read_txt(document_path) if suffix == ".txt" else read_pdf(document_path)
