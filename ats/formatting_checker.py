"""
ats/formatting_checker.py
----------------------------
Structural checks: contact info completeness, section coverage, and
overall resume length. These are "does the resume have the right
skeleton" checks, as opposed to keyword_checker.py's "is the content
inside that skeleton strong" checks.
"""

from __future__ import annotations

from ats.schemas import CheckResult
from ats.scoring_rules import (
    ABS_MAX_WORDS,
    ABS_MIN_WORDS,
    CATEGORY_WEIGHTS,
    CONTACT_FIELD_WEIGHTS,
    IDEAL_MAX_WORDS,
    IDEAL_MIN_WORDS,
)
from parser.schemas import ContactInfo, ResumeSections
from utils.constants import RESUME_SECTIONS


def check_contact_completeness(contact: ContactInfo) -> CheckResult:
    """Score based on which contact fields are present, weighted by importance."""
    score = 0
    missing_required: list[str] = []
    missing_optional: list[str] = []

    for field, weight in CONTACT_FIELD_WEIGHTS.items():
        value = getattr(contact, field, None)
        if value:
            score += weight
        elif field in ("name", "email", "phone"):
            missing_required.append(field)
        else:
            missing_optional.append(field)

    if not missing_required and not missing_optional:
        message = "All contact fields detected, including LinkedIn and GitHub."
    elif missing_required:
        message = (
            "Missing required contact info: " + ", ".join(missing_required) + "."
            " ATS systems reject resumes without clear contact details."
        )
    else:
        message = (
            "Core contact info is present. Consider adding: "
            + ", ".join(missing_optional) + " to strengthen your profile."
        )

    return CheckResult(
        key="contact_details",
        name="Contact Details",
        score=float(score),
        weight=CATEGORY_WEIGHTS["contact_details"],
        message=message,
    )


def check_section_coverage(sections: ResumeSections) -> CheckResult:
    """Score based on how many of the standard resume sections were detected."""
    section_dict = sections.model_dump()
    present = [name for name in RESUME_SECTIONS if section_dict.get(name)]
    missing = [name for name in RESUME_SECTIONS if not section_dict.get(name)]

    score = (len(present) / len(RESUME_SECTIONS)) * 100

    if not missing:
        message = "All standard resume sections were detected."
    else:
        message = (
            f"Detected {len(present)}/{len(RESUME_SECTIONS)} standard sections. "
            "Missing: " + ", ".join(m.title() for m in missing) + "."
        )

    return CheckResult(
        key="section_coverage",
        name="Section Coverage",
        score=round(score, 1),
        weight=CATEGORY_WEIGHTS["section_coverage"],
        message=message,
    )


def check_resume_length(word_count: int) -> CheckResult:
    """Score resume length against ideal ranges — too short or too long both hurt ATS parsing."""
    if IDEAL_MIN_WORDS <= word_count <= IDEAL_MAX_WORDS:
        score = 100.0
        message = f"Resume length ({word_count} words) is in the ideal range."
    elif word_count < IDEAL_MIN_WORDS:
        if word_count < ABS_MIN_WORDS:
            score = max(0.0, (word_count / ABS_MIN_WORDS) * 40)
        else:
            span = IDEAL_MIN_WORDS - ABS_MIN_WORDS
            score = 40 + ((word_count - ABS_MIN_WORDS) / span) * 60
        message = (
            f"Resume looks short ({word_count} words). Consider adding more "
            "detail to your experience and projects sections."
        )
    else:  # word_count > IDEAL_MAX_WORDS
        if word_count > ABS_MAX_WORDS:
            score = max(0.0, 100 - ((word_count - ABS_MAX_WORDS) / 10))
        else:
            span = ABS_MAX_WORDS - IDEAL_MAX_WORDS
            score = 100 - ((word_count - IDEAL_MAX_WORDS) / span) * 60
        message = (
            f"Resume looks long ({word_count} words). Consider tightening "
            "it to keep only the most relevant, recent content."
        )

    return CheckResult(
        key="resume_length",
        name="Resume Length",
        score=round(max(0.0, min(100.0, score)), 1),
        weight=CATEGORY_WEIGHTS["resume_length"],
        message=message,
    )
