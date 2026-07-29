"""
parser/section_parser.py
--------------------------
Splits cleaned resume text into named sections (summary, education,
experience, projects, skills, certifications, achievements) by
detecting heading lines.

Heading detection is alias-based rather than a single fixed string,
since resumes phrase the same section many different ways
("Work Experience" vs "Professional Experience" vs "Employment
History", "Skills" vs "Technical Skills" vs "Core Competencies", etc).

This is intentionally heuristic — resumes have no fixed schema — so
every result also reports which sections it failed to find, which
downstream ATS scoring (Phase 4) uses to penalize missing sections.
"""

from __future__ import annotations

import re

from parser.schemas import ResumeSections
from utils.constants import RESUME_SECTIONS

# Canonical section -> list of heading phrases that map to it.
# Order within a section doesn't matter; longer/more specific phrases
# are matched first overall so "professional summary" doesn't get
# mistaken piecemeal.
SECTION_ALIASES: dict[str, list[str]] = {
    "summary": [
        "professional summary", "career summary", "summary",
        "career objective", "objective", "profile", "about me",
    ],
    "education": [
        "education", "academic background", "educational qualifications",
        "academic qualifications",
    ],
    "experience": [
        "work experience", "professional experience", "employment history",
        "experience", "work history",
    ],
    "projects": [
        "academic projects", "personal projects", "projects",
        "key projects",
    ],
    "skills": [
        "technical skills", "core competencies", "key skills",
        "skills", "areas of expertise",
    ],
    "certifications": [
        "certifications", "certificates", "licenses and certifications",
        "licenses & certifications",
    ],
    "achievements": [
        "achievements", "honors and awards", "honors & awards", "awards",
        "accomplishments",
    ],
}

# Flatten to a single list of (alias, canonical_section), longest alias first
# so more specific phrases win over shorter substrings.
_ALIAS_LOOKUP: list[tuple[str, str]] = sorted(
    (
        (alias, section)
        for section, aliases in SECTION_ALIASES.items()
        for alias in aliases
    ),
    key=lambda pair: len(pair[0]),
    reverse=True,
)

# A heading line is short — real resume content lines are rarely this brief
# AND exactly equal to a known alias.
_MAX_HEADING_WORDS = 5


def _normalize_line(line: str) -> str:
    """Lowercase, strip punctuation/colons, collapse whitespace for comparison."""
    line = line.strip().lower()
    line = re.sub(r"[:\-–—.]+$", "", line)  # trailing colon/dash/period
    line = re.sub(r"\s+", " ", line)
    return line.strip()


def _match_heading(line: str) -> str | None:
    """Return the canonical section name if `line` looks like a section heading."""
    normalized = _normalize_line(line)
    if not normalized or len(normalized.split()) > _MAX_HEADING_WORDS:
        return None

    for alias, section in _ALIAS_LOOKUP:
        if normalized == alias:
            return section
    return None


def parse_sections(cleaned_text: str) -> tuple[ResumeSections, list[str], list[str]]:
    """
    Split `cleaned_text` into sections.

    Returns (sections, detected_order, warnings):
      - sections: ResumeSections with each found section's raw text
      - detected_order: canonical section names in the order they appeared
      - warnings: e.g. which of the standard sections were not found
    """
    lines = cleaned_text.split("\n")

    # Find heading positions
    headings: list[tuple[int, str]] = []  # (line_index, canonical_section)
    for idx, line in enumerate(lines):
        section = _match_heading(line)
        if section:
            headings.append((idx, section))

    section_text: dict[str, list[str]] = {name: [] for name in RESUME_SECTIONS}
    detected_order: list[str] = []

    if not headings:
        # No headings detected at all — everything falls back into "summary"
        # so at least contact/entity extraction downstream has text to work with.
        section_text["summary"] = lines
    else:
        # Content before the first heading (often the professional summary
        # or just contact info — leave it out of any named section).
        for i, (line_idx, section) in enumerate(headings):
            start = line_idx + 1
            end = headings[i + 1][0] if i + 1 < len(headings) else len(lines)
            section_text[section].extend(lines[start:end])
            if section not in detected_order:
                detected_order.append(section)

    sections_dict = {}
    for name in RESUME_SECTIONS:
        content = "\n".join(l for l in section_text[name] if l.strip()).strip()
        sections_dict[name] = content if content else None

    sections = ResumeSections(**sections_dict)

    warnings: list[str] = []
    missing = [name for name in RESUME_SECTIONS if sections_dict[name] is None]
    if missing:
        warnings.append(
            "Could not detect these standard sections: " + ", ".join(missing)
        )

    return sections, detected_order, warnings
