"""
tests/test_phase9_comparison.py
-----------------------------------
Unit tests for the Phase 9 resume comparison pipeline.

diff_engine.py is pure (compares already-computed objects), so most
tests build synthetic ATSReport/SkillExtractionResult pairs directly
rather than re-running the full parse/score pipeline — that pipeline is
already covered by the Phase 2-4 test files. comparison_service.py
(the real end-to-end orchestration) is covered separately using real
DOCX files, cross-checked against calling parse_resume/extract_skills/
generate_ats_report directly.
"""

from ats.schemas import ATSReport, CheckResult
from comparison.comparison_service import compare_resumes
from comparison.diff_engine import (
    compute_ats_score_delta,
    compute_check_deltas,
    compute_keyword_delta,
    compute_skill_delta,
    compute_verdict,
)
from parser.schemas import SkillExtractionResult


def _make_ats_report(overall_score: float, check_scores: dict[str, float]) -> ATSReport:
    checks = [
        CheckResult(key=key, name=key.replace("_", " ").title(), score=score, weight=1 / len(check_scores), message="")
        for key, score in check_scores.items()
    ]
    return ATSReport(overall_score=overall_score, passed=overall_score >= 70, resume_word_count=300, checks=checks)


def _make_skill_result(detected: list[str]) -> SkillExtractionResult:
    return SkillExtractionResult(
        detected_by_category={"Programming": detected},
        missing_by_category={"Programming": []},
        all_detected=detected,
        all_known_categories=["Programming"],
    )


# --------------------------------------------------------------------------- #
# compute_ats_score_delta
# --------------------------------------------------------------------------- #

def test_ats_score_delta_positive_change():
    old_ats = _make_ats_report(60.0, {"a": 60})
    new_ats = _make_ats_report(72.0, {"a": 72})
    delta, pct = compute_ats_score_delta(old_ats, new_ats)
    assert delta == 12.0
    assert pct == 20.0  # 12/60 * 100


def test_ats_score_delta_negative_change():
    old_ats = _make_ats_report(80.0, {"a": 80})
    new_ats = _make_ats_report(70.0, {"a": 70})
    delta, pct = compute_ats_score_delta(old_ats, new_ats)
    assert delta == -10.0
    assert pct == -12.5


def test_ats_score_delta_zero_old_score_returns_none_percent():
    old_ats = _make_ats_report(0.0, {"a": 0})
    new_ats = _make_ats_report(40.0, {"a": 40})
    delta, pct = compute_ats_score_delta(old_ats, new_ats)
    assert delta == 40.0
    assert pct is None  # must be None ("N/A"), never a ZeroDivisionError or inf


def test_ats_score_delta_identical_scores():
    old_ats = _make_ats_report(75.0, {"a": 75})
    new_ats = _make_ats_report(75.0, {"a": 75})
    delta, pct = compute_ats_score_delta(old_ats, new_ats)
    assert delta == 0.0
    assert pct == 0.0


# --------------------------------------------------------------------------- #
# compute_check_deltas
# --------------------------------------------------------------------------- #

def test_check_deltas_matches_by_key():
    old_ats = _make_ats_report(60.0, {"contact_details": 50, "resume_length": 70})
    new_ats = _make_ats_report(80.0, {"contact_details": 90, "resume_length": 70})
    deltas = compute_check_deltas(old_ats, new_ats)

    by_key = {d.key: d for d in deltas}
    assert by_key["contact_details"].delta == 40.0
    assert by_key["resume_length"].delta == 0.0
    assert len(deltas) == 2


def test_check_deltas_skips_keys_not_in_both_reports():
    old_ats = _make_ats_report(60.0, {"a": 50, "b": 60})
    new_ats = _make_ats_report(80.0, {"a": 90, "c": 70})  # "b" dropped, "c" added
    deltas = compute_check_deltas(old_ats, new_ats)
    keys = {d.key for d in deltas}
    assert keys == {"a"}  # only the key present in BOTH is compared


# --------------------------------------------------------------------------- #
# compute_skill_delta
# --------------------------------------------------------------------------- #

def test_skill_delta_added_and_removed():
    old_skills = _make_skill_result(["Python", "Java", "Git"])
    new_skills = _make_skill_result(["Python", "Django", "Docker"])
    delta = compute_skill_delta(old_skills, new_skills)

    assert set(delta.added) == {"Django", "Docker"}
    assert set(delta.removed) == {"Java", "Git"}
    assert set(delta.unchanged) == {"Python"}


def test_skill_delta_identical_skills():
    skills = _make_skill_result(["Python", "SQL"])
    delta = compute_skill_delta(skills, skills)
    assert delta.added == []
    assert delta.removed == []
    assert set(delta.unchanged) == {"Python", "SQL"}


def test_skill_delta_empty_to_populated():
    old_skills = _make_skill_result([])
    new_skills = _make_skill_result(["Python"])
    delta = compute_skill_delta(old_skills, new_skills)
    assert delta.added == ["Python"]
    assert delta.removed == []


# --------------------------------------------------------------------------- #
# compute_keyword_delta
# --------------------------------------------------------------------------- #

def test_keyword_delta_finds_new_terms():
    old_text = "Built REST APIs using Python and Django for a small team."
    new_text = "Architected scalable REST APIs using Python, Django, and Kubernetes for enterprise clients."
    delta = compute_keyword_delta(old_text, new_text)
    assert "kubernetes" in delta.added
    assert "enterprise" in delta.added or "clients" in delta.added


def test_keyword_delta_identical_text_has_no_changes():
    text = "Built REST APIs using Python and Django."
    delta = compute_keyword_delta(text, text)
    assert delta.added == []
    assert delta.removed == []


# --------------------------------------------------------------------------- #
# compute_verdict (deterministic, no LLM)
# --------------------------------------------------------------------------- #

def test_verdict_updated_wins_on_all_signals():
    old_skills = _make_skill_result(["Python"])
    new_skills = _make_skill_result(["Python", "Django", "Docker"])
    skill_delta = compute_skill_delta(old_skills, new_skills)
    keyword_delta = compute_keyword_delta("Built things.", "Built scalable enterprise systems using Kubernetes.")
    verdict = compute_verdict(ats_delta=15.0, skill_delta=skill_delta, keyword_delta=keyword_delta)
    assert verdict.better_resume == "Updated"
    assert len(verdict.reasons) == 3


def test_verdict_previous_wins_when_updated_regresses():
    old_skills = _make_skill_result(["Python", "Django", "Docker", "AWS"])
    new_skills = _make_skill_result(["Python"])
    skill_delta = compute_skill_delta(old_skills, new_skills)
    keyword_delta = compute_keyword_delta("Built scalable enterprise systems using Kubernetes.", "Built things.")
    verdict = compute_verdict(ats_delta=-20.0, skill_delta=skill_delta, keyword_delta=keyword_delta)
    assert verdict.better_resume == "Previous"


def test_verdict_tie_on_no_meaningful_change():
    skills = _make_skill_result(["Python"])
    skill_delta = compute_skill_delta(skills, skills)
    keyword_delta = compute_keyword_delta("Built REST APIs.", "Built REST APIs.")
    verdict = compute_verdict(ats_delta=0.0, skill_delta=skill_delta, keyword_delta=keyword_delta)
    assert verdict.better_resume == "Tie"


def test_verdict_reasons_are_human_readable_strings():
    skills = _make_skill_result(["Python"])
    skill_delta = compute_skill_delta(skills, skills)
    keyword_delta = compute_keyword_delta("text", "text")
    verdict = compute_verdict(ats_delta=5.0, skill_delta=skill_delta, keyword_delta=keyword_delta)
    assert all(isinstance(r, str) and r for r in verdict.reasons)


# --------------------------------------------------------------------------- #
# comparison_service.compare_resumes — full orchestration with real parsing
# --------------------------------------------------------------------------- #

def _write_docx(path, paragraphs):
    from docx import Document

    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    doc.save(str(path))


def test_compare_resumes_reuses_existing_pipeline(tmp_path):
    """
    Integration check: compare_resumes() must produce a result consistent
    with independently calling parse_resume/extract_skills/generate_ats_report
    directly — proving it reuses those functions rather than reimplementing
    parsing or scoring.
    """
    from ats.ats_score import generate_ats_report
    from parser.resume_parser import parse_resume
    from parser.skill_extractor import extract_skills

    old_paragraphs = [
        "John Smith", "john@example.com",
        "WORK EXPERIENCE", "Intern, Acme Corp", "Worked on Python automation.",
        "TECHNICAL SKILLS", "Python",
    ]
    new_paragraphs = [
        "John Smith", "john@example.com | 555-123-4567",
        "WORK EXPERIENCE", "Software Engineering Intern, Acme Corp",
        "- Built Python automation scripts, reducing manual work by 40%",
        "TECHNICAL SKILLS", "Python, Django, Docker, Git",
    ]

    old_path = tmp_path / "old.docx"
    new_path = tmp_path / "new.docx"
    _write_docx(old_path, old_paragraphs)
    _write_docx(new_path, new_paragraphs)

    result = compare_resumes(str(old_path), "old.docx", str(new_path), "new.docx")

    expected_old_parsed = parse_resume(str(old_path), original_filename="old.docx")
    expected_old_skills = extract_skills(expected_old_parsed.cleaned_text)
    expected_old_ats = generate_ats_report(expected_old_parsed, expected_old_skills)

    assert result.old_ats_score == expected_old_ats.overall_score
    assert result.old_filename == "old.docx"
    assert result.new_filename == "new.docx"
    assert "Django" in result.skill_delta.added
    assert "Docker" in result.skill_delta.added
    assert isinstance(result.ats_score_delta, float)
    assert result.verdict.better_resume in ("Previous", "Updated", "Tie")


def test_compare_resumes_identical_files_shows_no_changes(tmp_path):
    paragraphs = ["Jane Doe", "jane@example.com", "TECHNICAL SKILLS", "Python, SQL"]
    path_a = tmp_path / "a.docx"
    path_b = tmp_path / "b.docx"
    _write_docx(path_a, paragraphs)
    _write_docx(path_b, paragraphs)

    result = compare_resumes(str(path_a), "a.docx", str(path_b), "b.docx")

    assert result.ats_score_delta == 0.0
    assert result.skill_delta.added == []
    assert result.skill_delta.removed == []
    assert result.verdict.better_resume == "Tie"
