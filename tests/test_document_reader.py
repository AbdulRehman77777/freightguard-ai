from pathlib import Path

import pymupdf
import pytest

from freight_agent.document_reader import read_document
from freight_agent.exceptions import DocumentReadError


def test_valid_txt(tmp_path):
    path = tmp_path / "load.txt"
    path.write_text("Freight document", encoding="utf-8")
    assert read_document(path) == "Freight document"


def test_valid_selectable_pdf(tmp_path):
    path = tmp_path / "load.pdf"
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Freight document")
    pdf.save(path)
    pdf.close()
    assert "Freight document" in read_document(path)


def test_original_employer_pdf_contains_required_selectable_text():
    path = Path(__file__).parents[1] / "samples" / "original_document.pdf"
    text = read_document(path)
    expected_fragments = [
        "Apex Logistics Solutions LLC",
        "LD-994821",
        "Dallas, TX 75201",
        "Atlanta, GA 30303",
        "$2,200.00",
        "$350.00",
        "$2,800.00",
        "46,800 lbs",
    ]
    assert all(fragment in text for fragment in expected_fragments)


@pytest.mark.parametrize("suffix", [".txt", ".pdf"])
def test_empty_document(tmp_path, suffix):
    path = tmp_path / f"empty{suffix}"
    if suffix == ".pdf":
        pdf = pymupdf.open(); pdf.new_page(); pdf.save(path); pdf.close()
    else:
        path.write_text("", encoding="utf-8")
    with pytest.raises(DocumentReadError, match="No readable text"):
        read_document(path)


def test_unsupported_file(tmp_path):
    path = tmp_path / "load.docx"
    path.write_text("data")
    with pytest.raises(DocumentReadError, match="Unsupported"):
        read_document(path)


def test_missing_file(tmp_path):
    with pytest.raises(DocumentReadError, match="does not exist"):
        read_document(tmp_path / "missing.pdf")
