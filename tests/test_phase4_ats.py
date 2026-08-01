"""
tests/test_phase4_ats.py
--------------------------
Unit tests for the Phase 4 ATS scoring pipeline.
"""

from ats.ats_score import generate_ats_report
from ats.formatting_checker import (
    check_contact_completeness,
    check_resume_length,
    check_section_coverage,
)
from ats.keyword_checker import (
    check_action_verbs,
    check_bullet_usage,
    check_quantified_achievements,
)
from ats.scoring_rules import CATEGORY_WEIGHTS
from parser.entity_extractor import extract_contact_info
from parser.resume_parser import parse_resume
from parser.schemas import ContactInfo, ResumeSections
from parser.section_parser import parse_sections
from parser.skill_extractor import extract_skills
from parser.text_cleaner import clean_text


STRONG_EXPERIENCE = """Software Engineering Intern, Acme Corp
- Built REST APIs using Django and PostgreSQL, reducing query latency by 30%
- Led a team of 3 interns to deliver a feature ahead of schedule
- Automated deployment pipeline, cutting release time by 45%"""

WEAK_EXPERIENCE = """Software Engineering Intern, Acme Corp
Responsible for backend systems.
Worked on various tasks assigned by the manager."""


def test_category_weights_sum_to_one():
    assert abs(sum(CATEGORY_WEIGHTS.values()) - 1.0) < 1e-6


def test_check_contact_completeness_full():
    contact = ContactInfo(
        name="John Smith", email="j@example.com", phone="555-123-4567",
        linkedin="linkedin.com/in/john", github="github.com/john",
    )
    result = check_contact_completeness(contact)
    assert result.score == 100.0


def test_check_contact_completeness_missing_required():
    contact = ContactInfo(name="John Smith", email=None, phone=None)
    result = check_contact_completeness(contact)
    assert result.score == 30.0
    assert "email" in result.message and "phone" in result.message


def test_check_section_coverage_all_present():
    sections = ResumeSections(
        summary="x", education="x", experience="x", projects="x",
        skills="x", certifications="x", achievements="x",
    )
    result = check_section_coverage(sections)
    assert result.score == 100.0


def test_check_section_coverage_partial():
    sections = ResumeSections(summary="x", education="x", experience="x")
    result = check_section_coverage(sections)
    assert 0 < result.score < 100
    assert "projects" in result.message.lower()


def test_check_resume_length_ideal():
    result = check_resume_length(500)
    assert result.score == 100.0


def test_check_resume_length_too_short():
    result = check_resume_length(50)
    assert result.score < 40


def test_check_resume_length_too_long():
    result = check_resume_length(1500)
    assert result.score < 100


def test_check_bullet_usage_with_bullets():
    result = check_bullet_usage(STRONG_EXPERIENCE)
    assert result.score > 50


def test_check_bullet_usage_no_bullets():
    result = check_bullet_usage(WEAK_EXPERIENCE)
    assert result.score == 0.0


def test_check_action_verbs_strong():
    result = check_action_verbs(STRONG_EXPERIENCE)
    assert result.score > 50


def test_check_quantified_achievements_strong():
    result = check_quantified_achievements(STRONG_EXPERIENCE)
    assert result.score > 50


def test_check_quantified_achievements_none():
    result = check_quantified_achievements("- Helped the team with various duties")
    assert result.score == 0.0


def test_generate_ats_report_end_to_end():
    sample = f"""John Smith
john.smith@email.com | +1 555-123-4567
linkedin.com/in/johnsmith | github.com/johnsmith

PROFESSIONAL SUMMARY
Aspiring software engineer with a passion for backend systems.

EDUCATION
B.Tech in Computer Science, XYZ University, 2022-2026

WORK EXPERIENCE
{STRONG_EXPERIENCE}

PROJECTS
Resume Analyzer
- Built a Streamlit app to parse and score resumes, used by 50+ students

TECHNICAL SKILLS
Python, SQL, Django, Git, AWS, React, PostgreSQL, Docker

CERTIFICATIONS
AWS Certified Cloud Practitioner

ACHIEVEMENTS
Winner, University Hackathon 2025
"""
    cleaned = clean_text(sample)
    contact = extract_contact_info(cleaned)
    sections, order, _ = parse_sections(cleaned)
    skill_result = extract_skills(cleaned)

    from parser.schemas import ParsedResume

    parsed = ParsedResume(
        source_filename="sample.pdf",
        file_type="pdf",
        raw_text=sample,
        cleaned_text=cleaned,
        contact=contact,
        sections=sections,
        detected_section_order=order,
        parsing_warnings=[],
    )

    report = generate_ats_report(parsed, skill_result)
    assert 0 <= report.overall_score <= 100
    assert report.resume_word_count > 0
    assert len(report.checks) == 7
    # A well-formed sample with strong bullets, contact info, and skills
    # should score reasonably well.
    assert report.overall_score > 60
