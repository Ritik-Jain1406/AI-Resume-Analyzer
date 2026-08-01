"""
matching/job_matcher.py
---------------------------
Phase 5 orchestrator: runs semantic similarity, TF-IDF cosine similarity,
keyword coverage, and skill matching, then combines them into a single
weighted overall match percentage and a full MatchReport.

Weighting: when the semantic model is available, it carries the most
weight (it's the best single signal for "does this resume fit this
role"). If it's unavailable (no internet to download it), its weight is
redistributed across the other three signals so the report still adds
up to a meaningful 0-100 score rather than silently under-scoring.
"""

from __future__ import annotations

from matching.cosine_similarity import compute_cosine_similarity
from matching.keyword_match import compute_keyword_coverage
from matching.schemas import MatchReport
from matching.semantic_match import compute_semantic_similarity
from parser.skill_extractor import extract_skills
from parser.text_cleaner import normalize_for_matching
from utils.logger import get_logger

logger = get_logger(__name__)

# Weights used when the semantic model IS available (sum to 1.0)
WEIGHTS_WITH_SEMANTIC: dict[str, float] = {
    "semantic": 0.40,
    "cosine": 0.20,
    "keyword": 0.20,
    "skill": 0.20,
}

# Weights used when the semantic model is NOT available — semantic's
# share is redistributed proportionally across the remaining three (sum to 1.0)
WEIGHTS_WITHOUT_SEMANTIC: dict[str, float] = {
    "cosine": 0.35,
    "keyword": 0.30,
    "skill": 0.35,
}


def compute_job_match(resume_text: str, jd_text: str) -> MatchReport:
    """
    Match a resume against a job description and return a full MatchReport.

    `resume_text` should be the resume's cleaned full text (parser.text_cleaner.clean_text
    output). `jd_text` is the raw pasted/uploaded job description text.
    """
    warnings: list[str] = []

    if not resume_text.strip() or not jd_text.strip():
        warnings.append("Resume text or job description is empty — cannot compute a match.")
        return MatchReport(
            overall_match_percent=0.0,
            semantic_similarity=0.0,
            semantic_available=False,
            cosine_similarity=0.0,
            keyword_coverage=0.0,
            skill_match_percent=0.0,
            jd_word_count=len(jd_text.split()),
            warnings=warnings,
        )

    # --- Semantic similarity (embeddings, on original text for full context) ---
    semantic_score, semantic_warnings = compute_semantic_similarity(resume_text, jd_text)
    warnings.extend(semantic_warnings)
    semantic_available = semantic_score is not None

    # --- TF-IDF cosine similarity (on normalized text) ---
    resume_norm = normalize_for_matching(resume_text)
    jd_norm = normalize_for_matching(jd_text)
    cosine_score = compute_cosine_similarity(resume_norm, jd_norm)

    # --- Keyword coverage ---
    keyword_coverage, matched_keywords, missing_keywords = compute_keyword_coverage(
        resume_text, jd_text
    )

    # --- Skill match (reuses Phase 3's skill extractor on both texts) ---
    resume_skills = set(extract_skills(resume_text).all_detected)
    jd_skills = set(extract_skills(jd_text).all_detected)
    matched_skills = sorted(resume_skills & jd_skills)
    missing_skills = sorted(jd_skills - resume_skills)
    skill_match_percent = (
        round((len(matched_skills) / len(jd_skills)) * 100, 1) if jd_skills else 0.0
    )
    if not jd_skills:
        warnings.append(
            "No recognized skills were found in the job description, so "
            "skill match couldn't be scored — it's excluded from the "
            "overall match calculation."
        )

    # --- Combine into overall score ---
    if semantic_available and jd_skills:
        weights = WEIGHTS_WITH_SEMANTIC
        overall = (
            semantic_score * weights["semantic"]
            + cosine_score * weights["cosine"]
            + keyword_coverage * weights["keyword"]
            + skill_match_percent * weights["skill"]
        )
    elif semantic_available and not jd_skills:
        # Redistribute skill's weight across semantic/cosine/keyword
        overall = (
            semantic_score * 0.5 + cosine_score * 0.25 + keyword_coverage * 0.25
        )
    elif not semantic_available and jd_skills:
        weights = WEIGHTS_WITHOUT_SEMANTIC
        overall = (
            cosine_score * weights["cosine"]
            + keyword_coverage * weights["keyword"]
            + skill_match_percent * weights["skill"]
        )
    else:
        overall = cosine_score * 0.6 + keyword_coverage * 0.4

    overall = round(max(0.0, min(100.0, overall)), 1)

    logger.info(
        "Job match computed: overall={}, semantic_available={}",
        overall,
        semantic_available,
    )

    return MatchReport(
        overall_match_percent=overall,
        semantic_similarity=semantic_score if semantic_available else 0.0,
        semantic_available=semantic_available,
        cosine_similarity=cosine_score,
        keyword_coverage=keyword_coverage,
        matched_keywords=matched_keywords,
        missing_keywords=missing_keywords,
        skill_match_percent=skill_match_percent,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        jd_word_count=len(jd_text.split()),
        warnings=warnings,
    )
