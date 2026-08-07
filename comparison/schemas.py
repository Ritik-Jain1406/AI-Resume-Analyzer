"""
comparison/schemas.py
------------------------
Pydantic models for Phase 9 (Resume Comparison) output.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CheckDelta(BaseModel):
    """Before/after comparison for a single ATS check (e.g. 'Action Verbs')."""

    key: str
    name: str
    old_score: float
    new_score: float
    delta: float  # new_score - old_score


class SkillDelta(BaseModel):
    """Skills gained/lost/unchanged between the two resume versions."""

    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    unchanged: list[str] = Field(default_factory=list)


class KeywordDelta(BaseModel):
    """Keywords gained/lost between the two resume versions' own text."""

    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)


class ComparisonVerdict(BaseModel):
    """Deterministic, non-LLM summary of which version is stronger."""

    better_resume: str  # "Previous" | "Updated" | "Tie"
    reasons: list[str] = Field(default_factory=list)


class ResumeComparisonResult(BaseModel):
    """Full Phase 9 output: everything the Resume Comparison page displays."""

    old_filename: str
    new_filename: str

    old_ats_score: float
    new_ats_score: float
    ats_score_delta: float
    ats_improvement_percent: float | None  # None (-> "N/A") when old score is 0

    check_deltas: list[CheckDelta] = Field(default_factory=list)
    skill_delta: SkillDelta
    keyword_delta: KeywordDelta
    verdict: ComparisonVerdict
