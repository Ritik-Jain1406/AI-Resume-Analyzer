"""
matching/schemas.py
----------------------
Pydantic models for Phase 5 (Job Description Matching) output.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class MatchReport(BaseModel):
    """Full result of matching a resume against a job description."""

    overall_match_percent: float

    semantic_similarity: float  # 0-100, sentence-embedding based
    semantic_available: bool  # False if the embedding model couldn't be loaded

    cosine_similarity: float  # 0-100, TF-IDF based

    keyword_coverage: float  # 0-100, % of top JD keywords found in the resume
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)

    skill_match_percent: float  # 0-100, % of JD's known skills found in the resume
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)

    jd_word_count: int
    warnings: list[str] = Field(default_factory=list)
