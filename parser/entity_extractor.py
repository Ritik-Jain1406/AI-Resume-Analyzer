"""
parser/entity_extractor.py
-----------------------------
Extracts contact info (name, email, phone, LinkedIn, GitHub, portfolio)
from resume text.

Email/phone/LinkedIn/GitHub use regex (they're highly structured and
regex is both faster and more reliable than NER for these). Name
extraction is the hard part — resumes don't label "Name:" — so we use
a two-step approach:

  1. Try spaCy NER (PERSON entities) restricted to the first few lines,
     since the name is almost always at the very top.
  2. Fall back to a heuristic: the first non-empty line that doesn't
     look like an email/phone/URL/section heading and is short
     (2-4 title-cased words) is treated as the name.

The spaCy model is loaded lazily and the extractor degrades gracefully
(falls straight to the heuristic) if the model isn't installed, so a
missing `en_core_web_sm` doesn't crash the whole parsing pipeline.
"""

from __future__ import annotations

import re

from parser.schemas import ContactInfo
from utils.constants import EMAIL_REGEX, PHONE_REGEX, LINKEDIN_REGEX, GITHUB_REGEX
from utils.logger import get_logger

logger = get_logger(__name__)

_NLP = None
_NLP_LOAD_ATTEMPTED = False

# How many leading lines we consider "the header" when looking for a name
_HEADER_LINE_COUNT = 5

_GENERIC_URL_RE = re.compile(r"https?://[^\s|,]+", re.IGNORECASE)

_SECTION_HEADING_HINTS = (
    "summary", "objective", "education", "experience", "projects",
    "skills", "certifications", "achievements", "profile",
)


def _get_nlp():
    """Lazily load the spaCy model; return None if unavailable."""
    global _NLP, _NLP_LOAD_ATTEMPTED
    if _NLP is not None or _NLP_LOAD_ATTEMPTED:
        return _NLP

    _NLP_LOAD_ATTEMPTED = True
    try:
        import spacy

        _NLP = spacy.load("en_core_web_sm")
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "spaCy model 'en_core_web_sm' not available ({}); "
            "falling back to heuristic name extraction only.",
            exc,
        )
        _NLP = None
    return _NLP


def _extract_email(text: str) -> str | None:
    match = re.search(EMAIL_REGEX, text)
    return match.group(0) if match else None


def _extract_phone(text: str) -> str | None:
    match = re.search(PHONE_REGEX, text)
    if not match:
        return None
    candidate = match.group(0).strip()
    # Reject matches with too few digits (regex is loose, guards against
    # things like "2024 - 2025" being read as a phone number)
    if sum(ch.isdigit() for ch in candidate) < 7:
        return None
    return candidate


def _extract_linkedin(text: str) -> str | None:
    match = re.search(LINKEDIN_REGEX, text, re.IGNORECASE)
    return match.group(0) if match else None


def _extract_github(text: str) -> str | None:
    match = re.search(GITHUB_REGEX, text, re.IGNORECASE)
    return match.group(0) if match else None


def _extract_portfolio(text: str, linkedin: str | None, github: str | None) -> str | None:
    """Any other bare URL that isn't LinkedIn/GitHub is treated as a portfolio link."""
    for url in _GENERIC_URL_RE.findall(text):
        if linkedin and linkedin in url:
            continue
        if github and github in url:
            continue
        return url.rstrip(".,)")
    return None


def _looks_like_heading_or_contact(line: str) -> bool:
    lower = line.lower().strip()
    if not lower:
        return True
    if re.search(EMAIL_REGEX, line) or re.search(PHONE_REGEX, line):
        return True
    if _GENERIC_URL_RE.search(line):
        return True
    if any(hint in lower for hint in _SECTION_HEADING_HINTS):
        return True
    return False


def _heuristic_name(lines: list[str]) -> str | None:
    header = lines[:_HEADER_LINE_COUNT]
    for line in header:
        stripped = line.strip()
        if not stripped or _looks_like_heading_or_contact(stripped):
            continue
        words = stripped.split()
        if 1 <= len(words) <= 4 and all(w[0].isupper() for w in words if w[0].isalpha()):
            return stripped
    return None


def _spacy_name(text: str, lines: list[str]) -> str | None:
    nlp = _get_nlp()
    if nlp is None:
        return None

    header_text = "\n".join(lines[:_HEADER_LINE_COUNT])
    doc = nlp(header_text)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text.strip()
    return None


def extract_contact_info(cleaned_text: str) -> ContactInfo:
    """Extract all contact fields from cleaned resume text."""
    lines = [l for l in cleaned_text.split("\n") if l.strip()]

    email = _extract_email(cleaned_text)
    phone = _extract_phone(cleaned_text)
    linkedin = _extract_linkedin(cleaned_text)
    github = _extract_github(cleaned_text)
    portfolio = _extract_portfolio(cleaned_text, linkedin, github)

    name = _spacy_name(cleaned_text, lines) or _heuristic_name(lines)

    return ContactInfo(
        name=name,
        email=email,
        phone=phone,
        linkedin=linkedin,
        github=github,
        portfolio=portfolio,
    )
