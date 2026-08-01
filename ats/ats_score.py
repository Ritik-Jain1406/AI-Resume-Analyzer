"""
ats/ats_score.py
------------------
Phase 4 orchestrator: runs every individual check (formatting_checker +
keyword_checker), aggregates them into a weighted overall score, and
produces the final ATSReport with prioritized suggestions.
"""

from __future__ import annotations

from ats.formatting_checker import (
    check_contact_completeness,
    check_resume_length,
    check_section_coverage,
)
from ats.keyword_checker import (
    check_action_verbs,
    check_bullet_usage,
    check_keyword_richness,
    check_quantified_achievements,
)
from ats.schemas import ATSReport, CheckResult
from config import settings
from parser.schemas import ParsedResume, SkillExtractionResult
from utils.logger import get_logger

logger = get_logger(__name__)

# A check scoring below this is surfaced as a suggestion, ordered by
# how much overall score improving it would recover (weight * gap).
SUGGESTION_SCORE_THRESHOLD = 75.0


def _combined_experience_projects_text(parsed: ParsedResume) -> str:
    parts = [parsed.sections.experience, parsed.sections.projects]
    return "\n".join(p for p in parts if p)


def _build_suggestions(checks: list[CheckResult]) -> list[str]:
    """Rank weak checks by potential score impact and turn them into suggestions."""
    weak_checks = [c for c in checks if c.score < SUGGESTION_SCORE_THRESHOLD]
    weak_checks.sort(key=lambda c: c.weight * (100 - c.score), reverse=True)
    return [c.message for c in weak_checks]


def generate_ats_report(
    parsed: ParsedResume, skill_result: SkillExtractionResult
) -> ATSReport:
    """Run all Phase 4 checks against a parsed resume and produce the ATSReport."""
    word_count = len(parsed.cleaned_text.split())
    exp_proj_text = _combined_experience_projects_text(parsed)

    checks: list[CheckResult] = [
        check_contact_completeness(parsed.contact),
        check_section_coverage(parsed.sections),
        check_resume_length(word_count),
        check_keyword_richness(skill_result),
        check_bullet_usage(exp_proj_text),
        check_action_verbs(exp_proj_text),
        check_quantified_achievements(exp_proj_text),
    ]

    overall_score = round(sum(c.score * c.weight for c in checks), 1)
    passed = overall_score >= settings.ats_pass_threshold
    suggestions = _build_suggestions(checks)

    logger.info(
        "ATS report for {}: overall={}, passed={}",
        parsed.source_filename,
        overall_score,
        passed,
    )

    return ATSReport(
        overall_score=overall_score,
        passed=passed,
        resume_word_count=word_count,
        checks=checks,
        suggestions=suggestions,
    )
