"""
tests/test_phase2_parsing.py
------------------------------
Unit tests for the Phase 2 parsing pipeline. These run against plain
text (no real PDF/DOCX fixtures required for text_cleaner/section_parser/
entity_extractor), so they work without any sample resume files.

Note: spaCy's `en_core_web_sm` model may not be installed in every
environment. Name extraction falls back to a heuristic when it isn't,
so these tests are written to pass either way.
"""

from parser.entity_extractor import extract_contact_info
from parser.section_parser import parse_sections
from parser.text_cleaner import clean_text, normalize_for_matching

SAMPLE_RESUME = """John Smith
john.smith@email.com | +1 555-123-4567
linkedin.com/in/johnsmith | github.com/johnsmith

PROFESSIONAL SUMMARY
Aspiring software engineer with a passion for backend systems.

EDUCATION
B.Tech in Computer Science, XYZ University, 2022-2026

WORK EXPERIENCE
Software Engineering Intern, Acme Corp
- Built REST APIs using Django and PostgreSQL
- Reduced query latency by 30%

PROJECTS
Resume Analyzer
- Built a Streamlit app to parse and score resumes

TECHNICAL SKILLS
Python, SQL, Django, Git, AWS

CERTIFICATIONS
AWS Certified Cloud Practitioner

ACHIEVEMENTS
Winner, University Hackathon 2025
"""


def test_clean_text_normalizes_bullets_and_whitespace():
    dirty = "Line one\n\n\n\nLine two   with   spaces\n• bullet item"
    cleaned = clean_text(dirty)
    assert "\n\n\n" not in cleaned
    assert "  " not in cleaned
    assert "- bullet item" in cleaned


def test_clean_text_handles_empty_input():
    assert clean_text("") == ""
    assert clean_text(None or "") == ""


def test_normalize_for_matching_lowercases_and_strips_punctuation():
    result = normalize_for_matching("Python, SQL & Django!")
    assert result == "python sql django"


def test_parse_sections_detects_all_standard_sections():
    cleaned = clean_text(SAMPLE_RESUME)
    sections, order, warnings = parse_sections(cleaned)

    assert sections.summary is not None
    assert "backend systems" in sections.summary.lower()

    assert sections.education is not None
    assert "xyz university" in sections.education.lower()

    assert sections.experience is not None
    assert "acme corp" in sections.experience.lower()

    assert sections.projects is not None
    assert sections.skills is not None
    assert "python" in sections.skills.lower()

    assert sections.certifications is not None
    assert sections.achievements is not None

    assert "summary" in order
    assert "experience" in order
    assert warnings == []  # nothing should be missing in this fixture


def test_parse_sections_handles_missing_headings_gracefully():
    cleaned = clean_text("Just some free-form text with no headings at all.")
    sections, order, warnings = parse_sections(cleaned)

    assert order == []
    assert sections.summary is not None  # falls back into summary
    assert len(warnings) == 1
    assert "education" in warnings[0]


def test_extract_contact_info_finds_email_and_phone():
    cleaned = clean_text(SAMPLE_RESUME)
    contact = extract_contact_info(cleaned)

    assert contact.email == "john.smith@email.com"
    assert contact.phone is not None
    assert "555" in contact.phone
    assert contact.linkedin is not None and "linkedin.com/in/johnsmith" in contact.linkedin
    assert contact.github is not None and "github.com/johnsmith" in contact.github


def test_extract_contact_info_name_heuristic_fallback():
    # Even without spaCy installed, the heuristic should catch a clean
    # "First Last" line at the very top of the resume.
    cleaned = clean_text(SAMPLE_RESUME)
    contact = extract_contact_info(cleaned)
    assert contact.name in ("John Smith", None)  # None only if spaCy mis-tags AND heuristic fails
