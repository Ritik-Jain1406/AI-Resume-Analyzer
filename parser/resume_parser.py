"""
parser/resume_parser.py
--------------------------
Top-level orchestrator for Phase 2. Ties together file-type detection,
text extraction (PDF/DOCX), cleaning, entity extraction, and section
splitting into one call that returns a `ParsedResume`.

This is the single function the rest of the app (Streamlit pages,
later phases) should call — nothing outside `parser/` should import
`pdf_parser` or `docx_parser` directly.
"""

from __future__ import annotations

from pathlib import Path

from parser.docx_parser import extract_text_from_docx
from parser.entity_extractor import extract_contact_info
from parser.pdf_parser import extract_text_from_pdf
from parser.schemas import ParsedResume
from parser.section_parser import parse_sections
from parser.text_cleaner import clean_text
from utils.logger import get_logger
from utils.validators import ValidationError, validate_file_extension

logger = get_logger(__name__)


def parse_resume(file_path: str | Path, original_filename: str | None = None) -> ParsedResume:
    """
    Parse a resume file (PDF or DOCX) into a structured `ParsedResume`.

    `file_path` is where the file currently lives on disk.
    `original_filename` is the name to report in the result (useful when
    `file_path` is a temp file with a generated name) — defaults to the
    file_path's own name.
    """
    file_path = Path(file_path)
    display_name = original_filename or file_path.name
    extension = validate_file_extension(display_name)  # raises ValidationError if unsupported

    logger.info("Parsing resume: {}", display_name)

    if extension == ".pdf":
        raw_text, extraction_warnings = extract_text_from_pdf(file_path)
        file_type = "pdf"
    elif extension == ".docx":
        raw_text, extraction_warnings = extract_text_from_docx(file_path)
        file_type = "docx"
    else:
        # validate_file_extension already guards this, but keep it explicit
        raise ValidationError(f"Unsupported file extension: {extension}")

    cleaned = clean_text(raw_text)
    contact = extract_contact_info(cleaned)
    sections, detected_order, section_warnings = parse_sections(cleaned)

    warnings = [*extraction_warnings, *section_warnings]
    if not contact.email:
        warnings.append("Could not detect an email address.")
    if not contact.name:
        warnings.append("Could not confidently detect a name.")

    result = ParsedResume(
        source_filename=display_name,
        file_type=file_type,
        raw_text=raw_text,
        cleaned_text=cleaned,
        contact=contact,
        sections=sections,
        detected_section_order=detected_order,
        parsing_warnings=warnings,
    )

    logger.info(
        "Parsed {} — {} chars, {} sections detected, {} warning(s)",
        display_name,
        len(cleaned),
        len(detected_order),
        len(warnings),
    )
    return result
