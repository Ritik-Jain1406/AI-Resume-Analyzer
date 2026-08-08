"""
ai/schemas.py
----------------
Pydantic models validating Gemini's structured output for Phase 7.

Gemini is asked (via ai/prompts.py) to return JSON matching this shape
exactly. These models are the "robust validation mechanism" that catches
malformed, incomplete, or unexpectedly-shaped responses before they ever
reach the Streamlit UI — see ai/gemini_service.py and ai/recommendation.py
for how validation failures are turned into safe user-facing errors.

Priority/category fields use lenient validators rather than a strict
Literal type: LLM output occasionally drifts in casing or wording even
under JSON mode, and rejecting the entire response over "high priority"
vs "High Priority" would be worse than normalizing it.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

VALID_PRIORITIES = ("High Priority", "Medium Priority", "Low Priority")
VALID_JOB_CATEGORIES = ("Already Strong", "Improve", "Missing")


class SummarySuggestion(BaseModel):
    original: str | None = None
    improved: str = ""
    concise: str = ""
    target_role_focused: str | None = None


class ExperienceBulletSuggestion(BaseModel):
    original: str
    improved: str
    reason: str = ""


class ProjectSuggestion(BaseModel):
    project_name: str = "Project"
    original: str = ""
    improved_bullets: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    action_verbs: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class WeaknessItem(BaseModel):
    priority: str
    issue: str
    recommendation: str

    @field_validator("priority")
    @classmethod
    def _normalize_priority(cls, v: str) -> str:
        if v in VALID_PRIORITIES:
            return v
        lowered = (v or "").strip().lower()
        if "high" in lowered:
            return "High Priority"
        if "low" in lowered:
            return "Low Priority"
        return "Medium Priority"


class JobSpecificSuggestion(BaseModel):
    category: str
    detail: str

    @field_validator("category")
    @classmethod
    def _normalize_category(cls, v: str) -> str:
        if v in VALID_JOB_CATEGORIES:
            return v
        lowered = (v or "").strip().lower()
        if "strong" in lowered or "already" in lowered or "align" in lowered:
            return "Already Strong"
        if "missing" in lowered or "gap" in lowered:
            return "Missing"
        return "Improve"


VALID_DIFFICULTIES = ("Easy", "Medium", "Hard")


class InterviewQuestion(BaseModel):
    """One interview question, whether from the static bank or Gemini."""

    question: str
    difficulty: str  # "Easy" | "Medium" | "Hard"
    category: str  # "Skill" | "Project" | "Experience" | "Behavioral"
    source: str = "static"  # "static" | "gemini" — never fabricate this claim; set by the caller
    related_to: str | None = None  # e.g. the skill name or project name this question targets

    @field_validator("difficulty")
    @classmethod
    def _normalize_difficulty(cls, v: str) -> str:
        if v in VALID_DIFFICULTIES:
            return v
        lowered = (v or "").strip().lower()
        if "easy" in lowered or "beginner" in lowered:
            return "Easy"
        if "hard" in lowered or "advanced" in lowered or "senior" in lowered:
            return "Hard"
        return "Medium"


class InterviewPrepResult(BaseModel):
    """Full Phase 10 output: everything the Interview Prep page displays."""

    skill_questions: list[InterviewQuestion] = Field(default_factory=list)
    project_questions: list[InterviewQuestion] = Field(default_factory=list)
    behavioral_questions: list[InterviewQuestion] = Field(default_factory=list)
    gemini_available: bool = False
    warnings: list[str] = Field(default_factory=list)


class GeminiInterviewQuestionRaw(BaseModel):
    """
    Raw shape of one question in Gemini's project-questions response.
    Deliberately minimal — `category` and `source` are set by
    ai/interview_preparation.py itself after validation, never trusted
    from the model's own output (the model has no way to know whether
    its output should be labeled "gemini"; that's a fact about the
    pipeline, not the content).
    """

    question: str
    difficulty: str = "Medium"
    related_to: str | None = None


class GeminiInterviewQuestionsResponse(BaseModel):
    questions: list[GeminiInterviewQuestionRaw] = Field(default_factory=list)


class AIResumeSuggestions(BaseModel):
    """Full Phase 7 output: everything the AI Resume Suggestions page displays."""

    summary: SummarySuggestion | None = None
    experience: list[ExperienceBulletSuggestion] = Field(default_factory=list)
    projects: list[ProjectSuggestion] = Field(default_factory=list)
    weaknesses: list[WeaknessItem] = Field(default_factory=list)
    job_specific_suggestions: list[JobSpecificSuggestion] = Field(default_factory=list)
