"""Deterministic ATS-friendly document exporters."""

from io import BytesIO

from docx import Document
from docx.shared import Inches, Pt
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen.canvas import Canvas

from app.privacy import sanitize_filename


class ExportError(ValueError):
    """Raised when a document cannot be rendered safely."""


def render_docx(resume: str) -> tuple[str, bytes]:
    """Render resume text as a single-column, standard-font DOCX document."""
    if not resume.strip():
        raise ExportError("Cannot export an empty resume.")

    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)

    styles = document.styles
    normal = styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(10)

    for line in resume.splitlines():
        text = line.strip()
        if not text:
            continue
        if text.startswith(("- ", "* ")):
            document.add_paragraph(text[2:], style="List Bullet")
        else:
            document.add_paragraph(text)

    filename = sanitize_filename("tailored-resume.docx")
    output = BytesIO()
    document.save(output)
    return filename, output.getvalue()


def render_pdf(resume: str) -> tuple[str, bytes]:
    """Render resume text as a simple ATS-readable PDF."""
    if not resume.strip():
        raise ExportError("Cannot export an empty resume.")

    output = BytesIO()
    canvas = Canvas(output, pagesize=LETTER)
    width, height = LETTER
    x = 54
    y = height - 54
    canvas.setFont("Helvetica", 10)
    for line in resume.splitlines():
        if y < 54:
            canvas.showPage()
            canvas.setFont("Helvetica", 10)
            y = height - 54
        canvas.drawString(x, y, line.strip()[:120])
        y -= 14
    canvas.save()
    return sanitize_filename("tailored-resume.pdf"), output.getvalue()
