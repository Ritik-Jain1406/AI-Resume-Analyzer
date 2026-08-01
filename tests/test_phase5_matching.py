"""
tests/test_phase5_matching.py
--------------------------------
Unit tests for the Phase 5 job matching pipeline.

Note: sentence-transformers may not be installed/cached in every test
environment (it needs internet to download the model on first use).
compute_semantic_similarity() is designed to degrade gracefully in that
case (returns None + a warning), and compute_job_match() automatically
falls back to cosine/keyword/skill weighting — so these tests pass
correctly whether or not the semantic model is available.
"""

from matching.cosine_similarity import compute_cosine_similarity
from matching.job_matcher import compute_job_match
from matching.keyword_match import compute_keyword_coverage, extract_keywords

RESUME_TEXT = """
John Smith - Software Engineer
Experience building REST APIs with Python, Django, and PostgreSQL.
Deployed applications on AWS using Docker. Strong Git workflow experience.
Led a small team and mentored two junior engineers.
"""

JD_TEXT = """
We are hiring a Backend Engineer with experience in Python and Django.
The ideal candidate has worked with PostgreSQL, Docker, and AWS, and is
comfortable using Git in a collaborative team environment. Experience
mentoring junior engineers is a plus.
"""

UNRELATED_TEXT = """
This recipe describes how to bake a chocolate cake using flour, sugar,
eggs, butter, and cocoa powder, baked at 350 degrees for 35 minutes.
"""


def test_cosine_similarity_identical_texts_scores_high():
    score = compute_cosine_similarity(RESUME_TEXT, RESUME_TEXT)
    assert score > 95


def test_cosine_similarity_related_texts_scores_higher_than_unrelated():
    related_score = compute_cosine_similarity(RESUME_TEXT, JD_TEXT)
    unrelated_score = compute_cosine_similarity(RESUME_TEXT, UNRELATED_TEXT)
    assert related_score > unrelated_score


def test_cosine_similarity_empty_text_returns_zero():
    assert compute_cosine_similarity("", JD_TEXT) == 0.0
    assert compute_cosine_similarity(RESUME_TEXT, "") == 0.0


def test_extract_keywords_excludes_stopwords():
    keywords = extract_keywords(JD_TEXT, top_n=20)
    assert "the" not in keywords
    assert "and" not in keywords
    assert "python" in keywords or "django" in keywords


def test_keyword_coverage_matches_and_misses_correctly():
    coverage, matched, missing = compute_keyword_coverage(RESUME_TEXT, JD_TEXT)
    assert 0 <= coverage <= 100
    assert "python" in matched
    assert "django" in matched
    # every matched/missing keyword should be mutually exclusive
    assert not set(matched) & set(missing)


def test_keyword_coverage_empty_jd_returns_zero():
    coverage, matched, missing = compute_keyword_coverage(RESUME_TEXT, "")
    assert coverage == 0.0
    assert matched == []
    assert missing == []


def test_compute_job_match_end_to_end():
    report = compute_job_match(RESUME_TEXT, JD_TEXT)
    assert 0 <= report.overall_match_percent <= 100
    assert 0 <= report.cosine_similarity <= 100
    assert 0 <= report.keyword_coverage <= 100
    assert 0 <= report.skill_match_percent <= 100
    assert report.jd_word_count > 0
    # Django and Python appear in both -> should show up as matched skills
    assert "Python" in report.matched_skills
    assert "Django" in report.matched_skills


def test_compute_job_match_related_scores_higher_than_unrelated():
    related = compute_job_match(RESUME_TEXT, JD_TEXT)
    unrelated = compute_job_match(RESUME_TEXT, UNRELATED_TEXT)
    assert related.overall_match_percent > unrelated.overall_match_percent


def test_compute_job_match_handles_empty_jd():
    report = compute_job_match(RESUME_TEXT, "")
    assert report.overall_match_percent == 0.0
    assert report.warnings
