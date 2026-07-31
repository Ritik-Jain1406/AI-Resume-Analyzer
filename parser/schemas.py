"""
parser/schemas.py
------------------
Pydantic models describing the structured output of the resume parser.
Every downstream phase (ATS scoring, matching, skill gap, AI suggestions)
consumes a `ParsedResume` object rather than raw text, so this is the
single contract between "Phase 2: parsing" and everything after it.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ContactInfo(BaseModel):
    """Contact details extracted from the top of a resume."""

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None


class ResumeSections(BaseModel):
    """
    Raw text of each detected resume section.

    A missing section stays None rather than an empty string, so callers
    can distinguish "not found" from "found but empty".
    """

    summary: str | None = None
    education: str | None = None
    experience: str | None = None
    projects: str | None = None
    skills: str | None = None
    certifications: str | None = None
    achievements: str | None = None


class SkillExtractionResult(BaseModel):
    """
    Output of the Phase 3 skill extraction pipeline.

    `detected_by_category` / `missing_by_category` are keyed by every
    category present in the skills database (data/skills.csv), even if
    empty, so UI code can iterate categories without guarding for
    missing keys.
    """

    detected_by_category: dict[str, list[str]] = Field(default_factory=dict)
    missing_by_category: dict[str, list[str]] = Field(default_factory=dict)
    all_detected: list[str] = Field(default_factory=list)
    all_known_categories: list[str] = Field(default_factory=list)


class ParsedResume(BaseModel):
    """Full structured output of the Phase 2 parsing pipeline."""

    source_filename: str
    file_type: str  # "pdf" | "docx"
    raw_text: str
    cleaned_text: str
    contact: ContactInfo
    sections: ResumeSections
    detected_section_order: list[str] = Field(default_factory=list)
    parsing_warnings: list[str] = Field(default_factory=list)
