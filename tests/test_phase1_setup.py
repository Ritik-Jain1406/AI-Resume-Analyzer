"""
tests/test_phase1_setup.py
---------------------------
Smoke tests for the Phase 1 scaffold: config, logging, and validators
should all import and behave correctly before any real feature work
(parsing, ATS scoring, etc.) is layered on top.
"""

import pytest

from config import settings, ensure_directories, DATA_DIR
from utils.logger import get_logger
from utils.validators import (
    validate_file_extension,
    validate_file_size,
    validate_not_empty,
    ValidationError,
)
from utils.helper import percentage, truncate


def test_settings_load():
    assert settings.app_name == "AI Resume Analyzer"
    assert settings.ats_pass_threshold > 0


def test_ensure_directories_creates_data_dir():
    ensure_directories()
    assert DATA_DIR.exists()


def test_logger_returns_bound_logger():
    logger = get_logger(__name__)
    # Should not raise
    logger.info("Phase 1 smoke test logging call")


def test_validate_file_extension_accepts_pdf_and_docx():
    assert validate_file_extension("resume.pdf") == ".pdf"
    assert validate_file_extension("resume.docx") == ".docx"


def test_validate_file_extension_rejects_unsupported():
    with pytest.raises(ValidationError):
        validate_file_extension("resume.txt")


def test_validate_file_size_rejects_oversized_file():
    too_big = (settings.max_resume_size_mb + 1) * 1024 * 1024
    with pytest.raises(ValidationError):
        validate_file_size(too_big)


def test_validate_not_empty():
    assert validate_not_empty("  hello  ") == "hello"
    with pytest.raises(ValidationError):
        validate_not_empty("   ")


def test_percentage_helper():
    assert percentage(1, 4) == 25.0
    assert percentage(1, 0) == 0.0


def test_truncate_helper():
    assert truncate("short") == "short"
    assert truncate("a" * 200, max_length=10).endswith("\u2026")
