"""
comparison/comparison_service.py
------------------------------------
Phase 9 orchestrator. This is the ONLY module that calls the existing
Phase 2-4 pipeline (parse_resume, extract_skills, generate_ats_report) —
it calls each of them twice (once per resume version) and hands the
results to comparison.diff_engine, which never touches file parsing or
scoring itself.
"""

from __future__ import annotations

from pathlib import Path

from ats.ats_score import generate_ats_report
from comparison.diff_engine import (
    compute_ats_score_delta,
    compute_check_deltas,
    compute_keyword_delta,
    compute_skill_delta,
    compute_verdict,
)
from comparison.schemas import ResumeComparisonResult
from parser.resume_parser import parse_resume
from parser.skill_extractor import extract_skills
from utils.logger import get_logger

logger = get_logger(__name__)


def compare_resumes(
    old_file_path: str | Path,
    old_filename: str,
    new_file_path: str | Path,
    new_filename: str,
) -> ResumeComparisonResult:
    """
    Parse and score both resume versions (reusing the existing Phase 2-4
    pipeline, unmodified) and return the full comparison result.
    """
    old_parsed = parse_resume(old_file_path, original_filename=old_filename)
    new_parsed = parse_resume(new_file_path, original_filename=new_filename)

    old_skills = extract_skills(old_parsed.cleaned_text)
    new_skills = extract_skills(new_parsed.cleaned_text)

    old_ats = generate_ats_report(old_parsed, old_skills)
    new_ats = generate_ats_report(new_parsed, new_skills)

    ats_delta, improvement_percent = compute_ats_score_delta(old_ats, new_ats)
    check_deltas = compute_check_deltas(old_ats, new_ats)
    skill_delta = compute_skill_delta(old_skills, new_skills)
    keyword_delta = compute_keyword_delta(old_parsed.cleaned_text, new_parsed.cleaned_text)
    verdict = compute_verdict(ats_delta, skill_delta, keyword_delta)

    logger.info(
        "Compared resumes: ats_delta={}, improvement_percent={}, verdict={}",
        ats_delta,
        improvement_percent,
        verdict.better_resume,
    )

    return ResumeComparisonResult(
        old_filename=old_parsed.source_filename,
        new_filename=new_parsed.source_filename,
        old_ats_score=old_ats.overall_score,
        new_ats_score=new_ats.overall_score,
        ats_score_delta=ats_delta,
        ats_improvement_percent=improvement_percent,
        check_deltas=check_deltas,
        skill_delta=skill_delta,
        keyword_delta=keyword_delta,
        verdict=verdict,
    )
