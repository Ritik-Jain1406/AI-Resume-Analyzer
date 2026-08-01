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


class SkillGapItem(BaseModel):
    """One missing skill with its priority, resource, and time estimate."""

    skill: str
    category: str
    priority: str  # "High Priority" | "Medium Priority" | "Low Priority"
    mention_count: int  # how many times the skill was mentioned in the JD
    estimated_time: str  # e.g. "2-4 weeks" or "Ongoing practice"
    resource_name: str
    resource_url: str


class LearningPlan(BaseModel):
    """Full Phase 6 output: prioritized skill gaps + a suggested roadmap."""

    gap_items: list[SkillGapItem] = Field(default_factory=list)
    roadmap: list[str] = Field(default_factory=list)
    total_missing: int = 0
    high_priority_count: int = 0
    medium_priority_count: int = 0
    low_priority_count: int = 0
