"""
ai/interview_preparation.py
-------------------------------
Phase 10 orchestrator: builds the full interview question set from three
sources —

  1. Skill-based questions — static bank (data/interview_questions.csv),
     keyed off Phase 3's already-detected skills. Always available.
  2. Project/experience-based questions — reuses the existing
     ai/gemini_service.generate_json() (Phase 7's service, no duplicate
     API logic) with a new prompt from ai/prompts.py. Only generated on
     explicit request, and only when Gemini is configured.
  3. HR/Behavioral questions — static bank (ai/behavioral_questions.py).
     Always available, no Gemini involvement.

No new Gemini client/error-handling code lives here — every Gemini
interaction goes through the exact same gemini_service.generate_json()
Phase 7 already uses, so error handling, retries, and the JSON recovery
pipeline are all inherited for free.
"""

from __future__ import annotations

from functools import lru_cache

import pandas as pd
from pydantic import ValidationError

from ai.behavioral_questions import get_behavioral_questions
from ai.gemini_service import GeminiResponseError, generate_json, is_configured
from ai.prompts import (
    INTERVIEW_QUESTIONS_SYSTEM_INSTRUCTION,
    build_interview_questions_prompt,
)
from ai.schemas import (
    GeminiInterviewQuestionsResponse,
    InterviewPrepResult,
    InterviewQuestion,
)
from config import settings
from parser.schemas import SkillExtractionResult
from utils.logger import get_logger

logger = get_logger(__name__)

# Generic fallback used when a detected skill has no curated question —
# every detected skill produces at least one question, never a silent gap.
_FALLBACK_QUESTION_TEMPLATE = "What projects have you used {skill} in, and what challenges did you face?"


@lru_cache(maxsize=1)
def load_interview_question_bank() -> pd.DataFrame:
    """Load and cache the static skill-based question bank from CSV."""
    path = settings.interview_questions_csv
    if not path.exists():
        logger.error("Interview question bank not found at {}", path)
        return pd.DataFrame(columns=["skill", "difficulty", "question"])

    df = pd.read_csv(path)
    for col in ("skill", "difficulty", "question"):
        df[col] = df[col].astype(str).str.strip()
    return df


def get_skill_questions(skill_result: SkillExtractionResult) -> list[InterviewQuestion]:
    """
    Build skill-based questions for every detected skill.

    Skills with curated bank entries get those questions (one per
    difficulty tier where available); skills without any curated entry
    get a single generic fallback question rather than being skipped.
    """
    if not skill_result.all_detected:
        return []

    bank = load_interview_question_bank()
    questions: list[InterviewQuestion] = []

    for skill in skill_result.all_detected:
        skill_rows = bank[bank["skill"] == skill] if not bank.empty else bank
        if skill_rows is not None and not skill_rows.empty:
            for _, row in skill_rows.iterrows():
                questions.append(
                    InterviewQuestion(
                        question=row["question"],
                        difficulty=row["difficulty"],
                        category="Skill",
                        source="static",
                        related_to=skill,
                    )
                )
        else:
            questions.append(
                InterviewQuestion(
                    question=_FALLBACK_QUESTION_TEMPLATE.format(skill=skill),
                    difficulty="Medium",
                    category="Skill",
                    source="static",
                    related_to=skill,
                )
            )

    return questions


def get_project_questions(
    experience_text: str | None, projects_text: str | None
) -> tuple[list[InterviewQuestion], list[str]]:
    """
    Generate project/experience-grounded questions via Gemini.

    Returns (questions, warnings). Never raises — a Gemini failure
    (missing key, network issue, malformed response) is surfaced as a
    warning string, and the caller falls back to skill + behavioral
    questions only, exactly like Phase 7's graceful-degradation pattern.
    """
    warnings: list[str] = []

    if not (experience_text or "").strip() and not (projects_text or "").strip():
        return [], []

    if not is_configured():
        warnings.append(
            "Gemini API key is not configured — project-specific questions are "
            "unavailable. Skill-based and behavioral questions still work fully."
        )
        return [], warnings

    prompt = build_interview_questions_prompt(experience_text, projects_text)
    logger.info("Requesting project interview questions (prompt_chars={})", len(prompt))

    try:
        data = generate_json(INTERVIEW_QUESTIONS_SYSTEM_INSTRUCTION, prompt)
        raw = GeminiInterviewQuestionsResponse.model_validate(data)
    except ValidationError as exc:
        logger.warning("Gemini interview-questions response failed schema validation ({} error(s))", len(exc.errors()))
        warnings.append("Gemini's project questions couldn't be parsed. Please try regenerating.")
        return [], warnings
    except GeminiResponseError as exc:
        warnings.append(str(exc))
        return [], warnings
    except Exception as exc:  # noqa: BLE001 - GeminiConfigError/GeminiAPIError, already safe messages
        warnings.append(str(exc))
        return [], warnings

    questions = [
        InterviewQuestion(
            question=item.question,
            difficulty=item.difficulty,
            category="Project",
            source="gemini",
            related_to=item.related_to,
        )
        for item in raw.questions
    ]
    logger.info("Generated {} project-based interview question(s)", len(questions))
    return questions, warnings


def build_interview_prep(
    skill_result: SkillExtractionResult,
    experience_text: str | None,
    projects_text: str | None,
    include_project_questions: bool = False,
) -> InterviewPrepResult:
    """
    Build the full Phase 10 result: skill-based + behavioral questions
    always included; project-based questions included only when
    `include_project_questions` is True (i.e. the user explicitly
    clicked "Generate" — this function never calls Gemini on its own
    initiative).
    """
    skill_questions = get_skill_questions(skill_result)
    behavioral_questions = get_behavioral_questions()

    project_questions: list[InterviewQuestion] = []
    warnings: list[str] = []
    if include_project_questions:
        project_questions, warnings = get_project_questions(experience_text, projects_text)

    return InterviewPrepResult(
        skill_questions=skill_questions,
        project_questions=project_questions,
        behavioral_questions=behavioral_questions,
        gemini_available=is_configured(),
        warnings=warnings,
    )
