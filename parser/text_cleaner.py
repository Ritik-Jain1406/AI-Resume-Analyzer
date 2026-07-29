"""
parser/text_cleaner.py
------------------------
Normalizes raw text pulled from PDFs/DOCX files before it's handed to
entity extraction and section parsing. PDF extraction in particular
tends to produce broken hyphenation, stray bullet glyphs, repeated
blank lines, and inconsistent whitespace — this module fixes the most
common of those issues without altering meaningful content.
"""

from __future__ import annotations

import re
import unicodedata

# Common bullet glyphs PDFs export as literal characters
_BULLET_CHARS = "•●◦▪‣∙·–—"

# A run of whitespace-only line(s) collapses to a single blank line
_MULTI_BLANK_LINE_RE = re.compile(r"\n\s*\n\s*\n+")

# Trailing/leading whitespace on each line
_LINE_TRIM_RE = re.compile(r"[ \t]+\n")

# Hyphenated line breaks e.g. "develop-\nment" -> "development"
_HYPHEN_BREAK_RE = re.compile(r"(\w)-\n(\w)")

# Multiple spaces/tabs collapse to one space
_MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")


def clean_text(raw_text: str) -> str:
    """Run the full cleaning pipeline and return normalized text."""
    if not raw_text:
        return ""

    text = unicodedata.normalize("NFKC", raw_text)
    text = _normalize_bullets(text)
    text = _HYPHEN_BREAK_RE.sub(r"\1\2", text)
    text = _LINE_TRIM_RE.sub("\n", text)
    text = _MULTI_SPACE_RE.sub(" ", text)
    text = _MULTI_BLANK_LINE_RE.sub("\n\n", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return text.strip()


def _normalize_bullets(text: str) -> str:
    """Replace assorted bullet glyphs with a single consistent '- ' marker."""
    for ch in _BULLET_CHARS:
        text = text.replace(ch, "-")
    return text


def normalize_for_matching(text: str) -> str:
    """
    A more aggressive normalization used only for semantic/keyword
    matching (Phase 5) — lowercases and strips punctuation. Kept
    separate from `clean_text` because display text should stay
    human-readable, while match text should be maximally normalized.
    """
    text = clean_text(text).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = _MULTI_SPACE_RE.sub(" ", text)
    return text.strip()
