"""Deterministic text extraction. pdfplumber primary; tesseract fallback TODO.

Per ROADMAP M2 risk mitigation, image-only PDFs are out of scope for the
hackathon demo. We require text-based PDFs and raise a clear error
otherwise. Tesseract integration would slot in at the marked TODO.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


BBox = tuple[float, float, float, float]


class OcrUnavailableError(RuntimeError):
    """Raised when a PDF page yields no extractable text and no OCR fallback exists."""


@dataclass(frozen=True)
class PageText:
    pdf_page: int
    text: str
    bboxes: list[BBox] | None = field(default=None)


def extract_text(file_path: Path | str) -> list[PageText]:
    """Return per-page text. Pages are 1-indexed.

    Raises:
        FileNotFoundError: file missing.
        OcrUnavailableError: a page produced no text (image-only PDF or
            scan); tesseract fallback is the future remedy.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")

    import pdfplumber

    pages: list[PageText] = []
    with pdfplumber.open(str(path)) as pdf:
        for idx, page in enumerate(pdf.pages, start=1):
            text = (page.extract_text() or "").strip()
            if not text:
                # TODO(M2-stretch): plug tesseract here. For now we raise so
                # the caller surfaces a clear error instead of silently
                # producing TaxFacts with empty source text.
                raise OcrUnavailableError(
                    f"Page {idx} of {path.name} yielded no extractable text. "
                    f"Image-only PDFs are not supported in M2 (text-based only)."
                )
            pages.append(PageText(pdf_page=idx, text=text, bboxes=None))
    return pages


def page_count(file_path: Path | str) -> int:
    """Lightweight page count without full text extraction."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")
    import pdfplumber

    with pdfplumber.open(str(path)) as pdf:
        return len(pdf.pages)
