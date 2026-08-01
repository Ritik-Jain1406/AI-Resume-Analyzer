"""
ai/recommendation.py
------------------------
Phase 7 orchestrator: assembles context from the existing Phase 1-6
outputs (parsed resume, detected skills, ATS report, and optionally job
match / skill gap), builds the prompt, calls the Gemini service, and
validates the response into an AIResumeSuggestions object.

This is the only place that decides what resume data is sent to
Gemini — see ai/prompts.py for what's included/excluded.
"""

from __future__ import annotations

from pydantic import ValidationError

from ai.gemini_service import GeminiResponseError, generate_json
from ai.prompts import SYSTEM_INSTRUCTION, build_suggestions_prompt
from ai.schemas import AIResumeSuggestions
from ats.schemas import ATSReport
from matching.schemas import LearningPlan, MatchReport
from parser.schemas import ParsedResume, SkillExtractionResult
from utils.logger import get_logger

logger = get_logger(__name__)


def generate_resume_suggestions(
    parsed: ParsedResume,
    skill_result: SkillExtractionResult,
    ats_report: ATSReport,
    target_role: str = "",
    match_report: MatchReport | None = None,
    learning_plan: LearningPlan | None = None,
) -> AIResumeSuggestions:
    """
    Generate AI-powered resume suggestions using Gemini.

    Raises a GeminiServiceError subclass (see ai.gemini_service) on any
    failure — missing/invalid key, network issue, rate limit, or a
    malformed response. Every exception message from this call chain is
    already safe to show directly in the UI.
    """
    if not parsed.cleaned_text.strip():
        raise GeminiResponseError(
            "This resume has no extracted text to generate suggestions from."
        )

    prompt = build_suggestions_prompt(
        parsed=parsed,
        skill_result=skill_result,
        ats_report=ats_report,
        target_role=target_role,
        match_report=match_report,
        learning_plan=learning_plan,
    )

    # Log only technical metadata — never resume content or the API key.
    logger.info("Requesting AI resume suggestions (prompt_chars={})", len(prompt))

    data = generate_json(SYSTEM_INSTRUCTION, prompt)

    try:
        suggestions = AIResumeSuggestions.model_validate(data)
    except ValidationError as exc:
        logger.warning(
            "Gemini response failed schema validation ({} error(s))", len(exc.errors())
        )
        raise GeminiResponseError(
            "Gemini's response didn't match the expected format. Please try regenerating."
        ) from exc

    logger.info(
        "AI suggestions generated: {} experience, {} projects, {} weaknesses, {} job-specific",
        len(suggestions.experience),
        len(suggestions.projects),
        len(suggestions.weaknesses),
        len(suggestions.job_specific_suggestions),
    )
    return suggestions
