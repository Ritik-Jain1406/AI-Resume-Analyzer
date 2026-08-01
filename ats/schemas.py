"""
ats/schemas.py
----------------
Pydantic models for Phase 4 (ATS Resume Checker) output.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CheckResult(BaseModel):
    """Result of one individual ATS check (e.g. 'Resume Length')."""

    key: str  # stable identifier, e.g. "resume_length"
    name: str  # human-readable label, e.g. "Resume Length"
    score: float  # 0-100, this check's own score
    weight: float  # fraction of the overall score this check contributes (sums to 1.0 across all checks)
    message: str  # human-readable explanation / suggestion


class ATSReport(BaseModel):
    """Full Phase 4 output: overall score, per-check breakdown, suggestions."""

    overall_score: float
    passed: bool
    resume_word_count: int
    checks: list[CheckResult] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
