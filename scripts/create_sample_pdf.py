"""Generate the repository's selectable-text sample PDF fixture."""

from pathlib import Path
import textwrap

from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "samples" / "freight_document.txt"
TARGET = ROOT / "samples" / "freight_document.pdf"


def main() -> None:
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    canvas = Canvas(str(TARGET), pagesize=letter)
    canvas.setTitle("Freight Rate Confirmation & Order Agreement")
    canvas.setFont("Helvetica", 11)
    x, y = 48, 744
    visual_lines = [part for line in lines for part in (textwrap.wrap(line, width=88) or [""])]
    for line in visual_lines:
        if y < 48:
            canvas.showPage(); canvas.setFont("Helvetica", 11); y = 744
        canvas.drawString(x, y, line)
        y -= 17
    canvas.save()


if __name__ == "__main__":
    main()
