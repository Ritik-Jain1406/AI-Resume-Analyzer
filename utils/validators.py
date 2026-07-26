"""
utils/validators.py
--------------------
Reusable validation helpers for file uploads and user input.
Kept dependency-free (aside from config) so they can be unit tested
in isolation.
"""

from __future__ import annotations

from pathlib import Path

from config import settings


class ValidationError(Exception):
    """Raised when an uploaded file or input fails validation."""


def validate_file_extension(filename: str) -> str:
    """
    Ensure the uploaded file has an allowed extension.

    Returns the lowercase extension (e.g. ".pdf") on success.
    Raises ValidationError otherwise.
    """
    extension = Path(filename).suffix.lower()
    if extension not in settings.allowed_resume_extensions:
        allowed = ", ".join(settings.allowed_resume_extensions)
        raise ValidationError(
            f"Unsupported file type '{extension}'. Allowed types: {allowed}"
        )
    return extension


def validate_file_size(size_bytes: int) -> None:
    """Ensure the uploaded file does not exceed the configured size limit."""
    max_bytes = settings.max_resume_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise ValidationError(
            f"File too large ({size_bytes / 1024 / 1024:.2f} MB). "
            f"Max allowed is {settings.max_resume_size_mb} MB."
        )


def validate_not_empty(text: str, field_name: str = "input") -> str:
    """Ensure a string field isn't empty/whitespace-only after stripping."""
    stripped = text.strip()
    if not stripped:
        raise ValidationError(f"{field_name} cannot be empty.")
    return stripped
