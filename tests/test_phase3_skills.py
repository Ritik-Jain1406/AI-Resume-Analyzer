"""
tests/test_phase3_skills.py
------------------------------
Unit tests for the Phase 3 skill extraction pipeline.
"""

from parser.skill_extractor import extract_skills, load_skills_db


SAMPLE_TEXT = """
TECHNICAL SKILLS
Python, SQL, Django, Git, AWS, ReactJS, Postgres, Docker

WORK EXPERIENCE
Built REST APIs using Django and deployed on AWS with Docker containers.
Collaborated closely with the team and led a small group of interns.
"""


def test_skills_db_loads_and_has_expected_categories():
    db = load_skills_db()
    assert not db.empty
    categories = set(db["category"].unique())
    assert {"Programming", "Frameworks", "Cloud", "Databases",
            "Developer Tools", "Soft Skills"}.issubset(categories)


def test_extract_skills_finds_exact_matches():
    result = extract_skills(SAMPLE_TEXT)
    assert "Python" in result.all_detected
    assert "SQL" in result.all_detected
    assert "Django" in result.all_detected
    assert "Git" in result.all_detected
    assert "AWS" in result.all_detected
    assert "Docker" in result.all_detected


def test_extract_skills_handles_aliases():
    result = extract_skills(SAMPLE_TEXT)
    # "ReactJS" -> alias -> "React"; "Postgres" -> alias -> "PostgreSQL"
    assert "React" in result.all_detected
    assert "PostgreSQL" in result.all_detected


def test_extract_skills_categorizes_correctly():
    result = extract_skills(SAMPLE_TEXT)
    assert "Python" in result.detected_by_category["Programming"]
    assert "Django" in result.detected_by_category["Frameworks"]
    assert "AWS" in result.detected_by_category["Cloud"]
    assert "PostgreSQL" in result.detected_by_category["Databases"]
    assert "Docker" in result.detected_by_category["Developer Tools"]


def test_extract_skills_missing_list_excludes_detected():
    result = extract_skills(SAMPLE_TEXT)
    assert "Python" not in result.missing_by_category["Programming"]
    assert "Java" in result.missing_by_category["Programming"]


def test_extract_skills_handles_empty_text():
    result = extract_skills("")
    assert result.all_detected == []


def test_extract_skills_no_false_positive_for_unrelated_text():
    result = extract_skills("The quick brown fox jumps over the lazy dog.")
    # "Go" is a known skill (Programming); make sure it doesn't spuriously
    # match inside unrelated words due to bad boundary handling.
    assert "Go" not in result.all_detected
