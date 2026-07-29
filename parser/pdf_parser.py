"""
parser/pdf_parser.py
---------------------
Extracts raw text from PDF resumes.

Strategy: try PyMuPDF (fitz) first — it's fast and handles most
text-based PDFs well. If it returns suspiciously little text (common
with PDFs that use unusual encodings or are lightly scanned), fall back
to pdfplumber, which is slower but sometimes recovers text PyMuPDF misses.
We deliberately do NOT do OCR here — a scanned/image-only PDF is out of
scope for Phase 2 and should surface as a clear warning, not silently
return nothing.
"""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF
import pdfplumber

from utils.logger import get_logger

logger = get_logger(__name__)

# If PyMuPDF extracts fewer characters than this per page (on average),
# we treat the extraction as unreliable and try the pdfplumber fallback.
MIN_CHARS_PER_PAGE = 20


def _extract_with_pymupdf(path: Path) -> str:
    text_parts: list[str] = []
    with fitz.open(path) as doc:
        for page in doc:
            text_parts.append(page.get_text("text"))
    return "\n".join(text_parts)


def _extract_with_pdfplumber(path: Path) -> str:
    text_parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_text_from_pdf(path: str | Path) -> tuple[str, list[str]]:
    """
    Extract raw text from a PDF file.

    Returns a tuple of (text, warnings). `warnings` is a list of
    human-readable strings to surface to the user (e.g. if the PDF
    looks scanned/image-only and no text could be recovered).
    """
    path = Path(path)
    warnings: list[str] = []

    try:
        text = _extract_with_pymupdf(path)
    except Exception as exc:  # noqa: BLE001 - we want to fall back on any failure
        logger.warning("PyMuPDF failed to open {}: {}", path.name, exc)
        text = ""

    page_count = _safe_page_count(path)
    avg_chars = (len(text) / page_count) if page_count else len(text)

    if avg_chars < MIN_CHARS_PER_PAGE:
        logger.info(
            "PyMuPDF extraction looked sparse for {} ({} chars/page avg), "
            "trying pdfplumber fallback",
            path.name,
            round(avg_chars, 1),
        )
        try:
            fallback_text = _extract_with_pdfplumber(path)
            if len(fallback_text) > len(text):
                text = fallback_text
        except Exception as exc:  # noqa: BLE001
            logger.warning("pdfplumber fallback also failed for {}: {}", path.name, exc)

    if not text.strip():
        warnings.append(
            "No extractable text was found in this PDF. It may be a "
            "scanned image without a text layer — try uploading a "
            "text-based export instead."
        )

    return text, warnings


def _safe_page_count(path: Path) -> int:
    try:
        with fitz.open(path) as doc:
            return doc.page_count
    except Exception:  # noqa: BLE001
        return 1
