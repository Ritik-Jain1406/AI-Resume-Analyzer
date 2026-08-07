"""
comparison/diff_engine.py
-----------------------------
Phase 9's only genuinely new logic: pure functions that compare two
already-computed result sets (two ATSReports, two SkillExtractionResults,
two chunks of resume text) and produce deltas.

Strictly pure, per the Phase 9 spec: nothing in this file parses a file,
extracts skills, or scores a resume — it only ever receives objects that
Phases 2-4 already computed. comparison_service.py is the only caller,
and it's the one responsible for calling parse_resume() / extract_skills()
/ generate_ats_report() twice.
"""

from __future__ import annotations

from ats.schemas import ATSReport
from comparison.schemas import CheckDelta, ComparisonVerdict, KeywordDelta, SkillDelta
from matching.keyword_match import extract_keywords
from parser.schemas import SkillExtractionResult


def compute_ats_score_delta(old_ats: ATSReport, new_ats: ATSReport) -> tuple[float, float | None]:
    """
    Return (point_delta, improvement_percent).

    improvement_percent is None when old_ats.overall_score == 0 — a
    percentage change from zero is undefined, and callers should render
    that as "N/A" rather than dividing by zero or showing a misleading
    infinite/huge percentage.
    """
    delta = round(new_ats.overall_score - old_ats.overall_score, 1)
    if old_ats.overall_score == 0:
        return delta, None
    improvement_percent = round((delta / old_ats.overall_score) * 100, 1)
    return delta, improvement_percent


def compute_check_deltas(old_ats: ATSReport, new_ats: ATSReport) -> list[CheckDelta]:
    """
    Per-check before/after comparison, matched by each check's stable `key`.

    Checks present in only one report (shouldn't normally happen, since
    both reports run the same fixed set of checks) are skipped rather
    than guessed at.
    """
    old_by_key = {c.key: c for c in old_ats.checks}
    new_by_key = {c.key: c for c in new_ats.checks}

    deltas = []
    for key in old_by_key:
        if key not in new_by_key:
            continue
        old_check = old_by_key[key]
        new_check = new_by_key[key]
        deltas.append(
            CheckDelta(
                key=key,
                name=new_check.name,
                old_score=old_check.score,
                new_score=new_check.score,
                delta=round(new_check.score - old_check.score, 1),
            )
        )
    return deltas


def compute_skill_delta(
    old_skills: SkillExtractionResult, new_skills: SkillExtractionResult
) -> SkillDelta:
    """Set difference between two Phase 3 skill-extraction results."""
    old_set = set(old_skills.all_detected)
    new_set = set(new_skills.all_detected)

    return SkillDelta(
        added=sorted(new_set - old_set),
        removed=sorted(old_set - new_set),
        unchanged=sorted(old_set & new_set),
    )


def compute_keyword_delta(old_text: str, new_text: str, top_n: int = 30) -> KeywordDelta:
    """
    Keyword gain/loss between the two resumes' own text (no job description
    involved here — reuses Phase 5's extract_keywords() against each
    resume's text directly).
    """
    old_keywords = set(extract_keywords(old_text, top_n=top_n))
    new_keywords = set(extract_keywords(new_text, top_n=top_n))

    return KeywordDelta(
        added=sorted(new_keywords - old_keywords),
        removed=sorted(old_keywords - new_keywords),
    )


def compute_verdict(
    ats_delta: float, skill_delta: SkillDelta, keyword_delta: KeywordDelta
) -> ComparisonVerdict:
    """
    Deterministic (no LLM) summary of which version is stronger.

    Simple point system across the three signals the spec calls out —
    ATS improvement, skills added vs. removed, keywords added vs.
    removed — each contributing at most +1/-1. This is intentionally a
    simple, explainable heuristic, not a weighted score: the goal is a
    quick, defensible "which one's better" read, with the reasons spelled
    out so the number is never a black box.
    """
    points = 0
    reasons: list[str] = []

    if ats_delta > 0:
        points += 1
        reasons.append(f"ATS score improved by {ats_delta:+.1f} points.")
    elif ats_delta < 0:
        points -= 1
        reasons.append(f"ATS score dropped by {abs(ats_delta):.1f} points.")
    else:
        reasons.append("ATS score is unchanged.")

    skills_added, skills_removed = len(skill_delta.added), len(skill_delta.removed)
    if skills_added > skills_removed:
        points += 1
        reasons.append(f"Gained {skills_added} skill(s), lost {skills_removed}.")
    elif skills_removed > skills_added:
        points -= 1
        reasons.append(f"Lost {skills_removed} skill(s), gained {skills_added}.")
    else:
        reasons.append(f"Skill count is unchanged ({skills_added} added, {skills_removed} removed).")

    kw_added, kw_removed = len(keyword_delta.added), len(keyword_delta.removed)
    if kw_added > kw_removed:
        points += 1
        reasons.append(f"Gained {kw_added} keyword(s), lost {kw_removed}.")
    elif kw_removed > kw_added:
        points -= 1
        reasons.append(f"Lost {kw_removed} keyword(s), gained {kw_added}.")
    else:
        reasons.append(f"Keyword count is unchanged ({kw_added} added, {kw_removed} removed).")

    if points > 0:
        better = "Updated"
    elif points < 0:
        better = "Previous"
    else:
        better = "Tie"

    return ComparisonVerdict(better_resume=better, reasons=reasons)
