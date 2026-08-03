"""
tests/test_phase8_dashboard.py
---------------------------------
Unit tests for the Phase 8 dashboard: chart data-shaping (visualization/
charts.py) and gating logic (visualization/dashboard.py).

Phase 8 is presentation-only, so these tests focus on:
  - each chart function returns a Figure whose trace data cardinality
    matches the input model (e.g. pie slice count == number of non-empty
    skill categories)
  - degenerate/empty inputs (zero skills, all-zero-ish ATS) don't raise
  - dashboard.py only renders the sections whose backing session-state
    data is actually present — it must never compute a new job match,
    a new semantic similarity score, or call Gemini itself
"""

import pytest

from ats.ats_score import generate_ats_report
from matching.job_matcher import compute_job_match
from matching.skill_gap import analyze_skill_gap
from parser.entity_extractor import extract_contact_info
from parser.schemas import ParsedResume, SkillExtractionResult
from parser.section_parser import parse_sections
from parser.skill_extractor import extract_skills
from parser.text_cleaner import clean_text
from visualization import charts


SAMPLE_RESUME = """John Smith
john.smith@email.com | +1 555-123-4567

PROFESSIONAL SUMMARY
Aspiring software engineer with a passion for backend systems.

WORK EXPERIENCE
Software Engineering Intern, Acme Corp
- Built REST APIs using Django and PostgreSQL, reducing query latency by 30%
- Led a team of 3 interns to deliver a feature ahead of schedule

PROJECTS
Resume Analyzer
- Built a Streamlit app to parse and score resumes, used by 50+ students

TECHNICAL SKILLS
Python, SQL, Django, Git, AWS, React, PostgreSQL, Docker
"""

JD_TEXT = """We are hiring a Backend Engineer with experience in Python,
Django, PostgreSQL, Docker, AWS, and Kubernetes. Git experience required."""


def _build_parsed_resume(text: str) -> ParsedResume:
    cleaned = clean_text(text)
    contact = extract_contact_info(cleaned)
    sections, order, _ = parse_sections(cleaned)
    return ParsedResume(
        source_filename="sample.pdf",
        file_type="pdf",
        raw_text=text,
        cleaned_text=cleaned,
        contact=contact,
        sections=sections,
        detected_section_order=order,
        parsing_warnings=[],
    )


@pytest.fixture
def full_pipeline_data():
    parsed = _build_parsed_resume(SAMPLE_RESUME)
    skills = extract_skills(parsed.cleaned_text)
    ats = generate_ats_report(parsed, skills)
    match = compute_job_match(parsed.cleaned_text, JD_TEXT)
    plan = analyze_skill_gap(match.missing_skills, JD_TEXT)
    return {"parsed": parsed, "skills": skills, "ats": ats, "match": match, "plan": plan}


# --------------------------------------------------------------------------- #
# Chart data-shaping tests
# --------------------------------------------------------------------------- #

def test_ats_score_gauge_returns_single_trace(full_pipeline_data):
    fig = charts.ats_score_gauge(full_pipeline_data["ats"])
    assert len(fig.data) == 1


def test_ats_weak_sections_bar_matches_check_count(full_pipeline_data):
    ats = full_pipeline_data["ats"]
    fig = charts.ats_weak_sections_bar(ats)
    bar = fig.data[0]
    assert len(bar.kwargs["x"]) == len(ats.checks)
    assert len(bar.kwargs["y"]) == len(ats.checks)


def test_ats_weak_sections_bar_sorted_ascending(full_pipeline_data):
    ats = full_pipeline_data["ats"]
    fig = charts.ats_weak_sections_bar(ats)
    scores = fig.data[0].kwargs["x"]
    assert scores == sorted(scores)


def test_resume_strength_radar_closes_the_loop(full_pipeline_data):
    ats = full_pipeline_data["ats"]
    fig = charts.resume_strength_radar(ats)
    radar = fig.data[0]
    assert len(radar.kwargs["r"]) == len(ats.checks) + 1
    assert len(radar.kwargs["theta"]) == len(ats.checks) + 1
    assert radar.kwargs["r"][0] == radar.kwargs["r"][-1]


def test_skill_distribution_pie_matches_nonempty_categories(full_pipeline_data):
    skills = full_pipeline_data["skills"]
    fig = charts.skill_distribution_pie(skills)
    pie = fig.data[0]
    expected = sum(1 for v in skills.detected_by_category.values() if v)
    assert len(pie.kwargs["labels"]) == expected
    assert len(pie.kwargs["values"]) == expected


def test_skill_distribution_pie_empty_state_does_not_raise():
    empty = SkillExtractionResult(
        detected_by_category={"Programming": []},
        missing_by_category={"Programming": ["Python"]},
        all_detected=[],
        all_known_categories=["Programming"],
    )
    fig = charts.skill_distribution_pie(empty)
    pie = fig.data[0]
    assert pie.kwargs["labels"] == ["No skills detected"]


def test_job_match_gauge_value_matches_report(full_pipeline_data):
    match = full_pipeline_data["match"]
    fig = charts.job_match_gauge(match)
    assert fig.data[0].kwargs["value"] == match.overall_match_percent


def test_job_match_signals_bar_has_four_signals(full_pipeline_data):
    match = full_pipeline_data["match"]
    fig = charts.job_match_signals_bar(match)
    bar = fig.data[0]
    assert bar.kwargs["x"] == ["Semantic", "Cosine", "Keyword", "Skill"]
    assert len(bar.kwargs["y"]) == 4


def test_job_match_signals_bar_semantic_unavailable_shows_zero():
    from matching.schemas import MatchReport

    match = MatchReport(
        overall_match_percent=40.0,
        semantic_similarity=0.0,
        semantic_available=False,
        cosine_similarity=50.0,
        keyword_coverage=30.0,
        skill_match_percent=20.0,
        jd_word_count=10,
    )
    fig = charts.job_match_signals_bar(match)
    bar = fig.data[0]
    assert bar.kwargs["y"][0] == 0  # semantic slot shows 0, not a fabricated value


def test_skill_gap_priority_bar_counts_sum_to_total(full_pipeline_data):
    plan = full_pipeline_data["plan"]
    fig = charts.skill_gap_priority_bar(plan)
    bar = fig.data[0]
    assert sum(bar.kwargs["y"]) == plan.total_missing


def test_skill_gap_priority_bar_empty_plan_does_not_raise():
    from matching.schemas import LearningPlan

    empty_plan = LearningPlan()
    fig = charts.skill_gap_priority_bar(empty_plan)
    bar = fig.data[0]
    assert sum(bar.kwargs["y"]) == 0


def test_ats_gauge_handles_zero_score():
    from ats.schemas import ATSReport

    zero_report = ATSReport(overall_score=0.0, passed=False, resume_word_count=0, checks=[])
    fig = charts.ats_score_gauge(zero_report)
    assert fig.data[0].kwargs["value"] == 0.0


def test_resume_strength_radar_handles_empty_checks_without_raising():
    from ats.schemas import ATSReport

    empty_report = ATSReport(overall_score=0.0, passed=False, resume_word_count=0, checks=[])
    fig = charts.resume_strength_radar(empty_report)
    assert fig.data[0].kwargs["r"] == []


# --------------------------------------------------------------------------- #
# Dashboard gating tests (session-state presence/absence -> what renders)
# --------------------------------------------------------------------------- #

class _FakeCol:
    def __init__(self, calls):
        self._calls = calls

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def metric(self, *a, **k):
        self._calls.append(("metric", a, k))

    def markdown(self, *a, **k):
        self._calls.append(("markdown", a))


@pytest.fixture
def fake_streamlit(monkeypatch):
    """Minimal streamlit stand-in that records every call, for gating assertions."""
    import sys
    import types as pytypes

    calls = []
    fake_st = pytypes.ModuleType("streamlit")

    def columns(n):
        return [_FakeCol(calls) for _ in range(n if isinstance(n, int) else len(n))]

    fake_st.columns = columns
    fake_st.metric = lambda *a, **k: calls.append(("metric", a, k))
    fake_st.info = lambda *a, **k: calls.append(("info", a, k))
    fake_st.subheader = lambda *a, **k: calls.append(("subheader", a, k))
    fake_st.divider = lambda *a, **k: calls.append(("divider",))
    fake_st.markdown = lambda *a, **k: calls.append(("markdown", a))
    fake_st.plotly_chart = lambda *a, **k: calls.append(("plotly_chart", a))
    fake_st.download_button = lambda *a, **k: calls.append(("download_button", a, k))

    monkeypatch.setitem(sys.modules, "streamlit", fake_st)
    monkeypatch.delitem(sys.modules, "visualization.dashboard", raising=False)
    from visualization import dashboard as dashboard_module

    return dashboard_module, calls


def test_dashboard_no_resume_shows_no_charts(fake_streamlit):
    dashboard_module, calls = fake_streamlit
    dashboard_module.render_dashboard(None, None, None, None, None, None)
    plotly_calls = [c for c in calls if c[0] == "plotly_chart"]
    info_calls = [c for c in calls if c[0] == "info"]
    assert len(plotly_calls) == 0
    assert len(info_calls) >= 1


def test_dashboard_without_job_match_omits_match_charts(fake_streamlit, full_pipeline_data):
    dashboard_module, calls = fake_streamlit
    dashboard_module.render_dashboard(
        parsed=full_pipeline_data["parsed"],
        ats_report=full_pipeline_data["ats"],
        skill_result=full_pipeline_data["skills"],
        match_report=None,
        learning_plan=None,
        ai_suggestions=None,
    )
    plotly_calls = [c for c in calls if c[0] == "plotly_chart"]
    info_calls = [c for c in calls if c[0] == "info"]
    assert len(plotly_calls) == 4
    assert any("Job Matching" in str(c[1]) for c in info_calls)
    assert any("AI Suggestions" in str(c[1]) for c in info_calls)


def test_dashboard_with_job_match_and_skill_gap_renders_all_charts(fake_streamlit, full_pipeline_data):
    dashboard_module, calls = fake_streamlit
    dashboard_module.render_dashboard(
        parsed=full_pipeline_data["parsed"],
        ats_report=full_pipeline_data["ats"],
        skill_result=full_pipeline_data["skills"],
        match_report=full_pipeline_data["match"],
        learning_plan=full_pipeline_data["plan"],
        ai_suggestions=None,
    )
    plotly_calls = [c for c in calls if c[0] == "plotly_chart"]
    assert len(plotly_calls) == 7


def test_dashboard_always_offers_summary_download(fake_streamlit, full_pipeline_data):
    dashboard_module, calls = fake_streamlit
    dashboard_module.render_dashboard(
        parsed=full_pipeline_data["parsed"],
        ats_report=full_pipeline_data["ats"],
        skill_result=full_pipeline_data["skills"],
        match_report=None,
        learning_plan=None,
        ai_suggestions=None,
    )
    download_calls = [c for c in calls if c[0] == "download_button"]
    assert len(download_calls) == 1


def test_pipeline_overview_reflects_available_stages(fake_streamlit, full_pipeline_data):
    dashboard_module, calls = fake_streamlit
    dashboard_module.render_pipeline_overview(
        parsed=full_pipeline_data["parsed"],
        ats_report=full_pipeline_data["ats"],
        skill_result=full_pipeline_data["skills"],
        match_report=None,
        learning_plan=None,
        ai_suggestions=None,
    )
    markdown_calls = [c for c in calls if c[0] == "markdown"]
    rendered_icons = "".join(str(c[1]) for c in markdown_calls)
    assert rendered_icons.count("✅") == 3
    assert rendered_icons.count("⬜") == 3


def test_ai_suggestions_summary_shows_prompt_when_absent(fake_streamlit):
    dashboard_module, calls = fake_streamlit
    dashboard_module.render_ai_suggestions_summary(None)
    info_calls = [c for c in calls if c[0] == "info"]
    assert len(info_calls) == 1
    assert "Generate Suggestions" in str(info_calls[0][1])


# --------------------------------------------------------------------------- #
# Regression safety: Phase 1-7 pipeline still produces data Phase 8 can consume
# --------------------------------------------------------------------------- #

def test_phase_1_through_6_pipeline_still_produces_consumable_data(full_pipeline_data):
    """
    Not a re-test of Phase 1-6 logic itself (see their own test files) —
    just confirms the objects those phases produce still have the exact
    shape Phase 8's chart functions expect, since Phase 8 must not modify
    any of those modules.
    """
    assert full_pipeline_data["parsed"].cleaned_text
    assert full_pipeline_data["ats"].checks
    assert isinstance(full_pipeline_data["skills"].detected_by_category, dict)
    assert full_pipeline_data["match"].overall_match_percent >= 0
    assert full_pipeline_data["plan"].total_missing >= 0
