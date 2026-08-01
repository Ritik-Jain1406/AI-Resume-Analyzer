"""
ats/keyword_checker.py
-------------------------
Content-quality checks: keyword/skill richness, bullet-point usage,
action-verb strength, and quantified achievements. These look at what's
*inside* the resume's sections, as opposed to formatting_checker.py's
structural checks.
"""

from __future__ import annotations

import re

from ats.schemas import CheckResult
from ats.scoring_rules import (
    ACTION_VERBS,
    CATEGORY_WEIGHTS,
    SKILL_COUNT_SCORE_TIERS,
    WEAK_OPENING_PHRASES,
)
from parser.schemas import SkillExtractionResult

_NUMBER_OR_PERCENT_RE = re.compile(r"\d")


def _bullet_lines(text: str | None) -> list[str]:
    """Return the content of each bullet line (lines starting with '- ')."""
    if not text:
        return []
    lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- "):
            lines.append(stripped[2:].strip())
        elif stripped.startswith("-") and len(stripped) > 1:
            lines.append(stripped[1:].strip())
    return lines


def _non_empty_lines(text: str | None) -> list[str]:
    if not text:
        return []
    return [l for l in text.split("\n") if l.strip()]


def check_keyword_richness(skill_result: SkillExtractionResult) -> CheckResult:
    """Score based on how many known skills were detected anywhere in the resume."""
    count = len(skill_result.all_detected)

    score = 0.0
    for threshold, tier_score in SKILL_COUNT_SCORE_TIERS:
        if count >= threshold:
            score = tier_score
            break

    if count == 0:
        message = "No recognized technical or soft skills detected. Add a clear Skills section."
    elif score < 65:
        message = f"Only {count} skill(s) detected. Listing more relevant skills will help you pass keyword filters."
    else:
        message = f"{count} skill(s) detected — good keyword coverage."

    return CheckResult(
        key="keyword_richness",
        name="Keyword Richness",
        score=score,
        weight=CATEGORY_WEIGHTS["keyword_richness"],
        message=message,
    )


def check_bullet_usage(experience_and_projects_text: str) -> CheckResult:
    """Score the proportion of experience/projects content written as bullets."""
    lines = _non_empty_lines(experience_and_projects_text)
    bullets = _bullet_lines(experience_and_projects_text)

    if not lines:
        return CheckResult(
            key="bullet_usage",
            name="Bullet Point Usage",
            score=0.0,
            weight=CATEGORY_WEIGHTS["bullet_usage"],
            message="No Experience or Projects content detected to evaluate.",
        )

    ratio = len(bullets) / len(lines)
    score = round(min(ratio, 1.0) * 100, 1)

    if not bullets:
        message = (
            "No bullet points detected in Experience/Projects. ATS systems "
            "and recruiters both parse bulleted achievements far better "
            "than paragraphs."
        )
    elif score < 60:
        message = "Some content isn't in bullet form. Consider converting remaining prose into concise bullets."
    elif score < 85:
        message = (
            "Most content is bulleted, but some lines are still written as "
            "plain paragraphs — convert them for full consistency."
        )
    else:
        message = "Experience and Projects are well-structured with bullet points."

    return CheckResult(
        key="bullet_usage",
        name="Bullet Point Usage",
        score=score,
        weight=CATEGORY_WEIGHTS["bullet_usage"],
        message=message,
    )


def check_action_verbs(experience_and_projects_text: str) -> CheckResult:
    """Score the proportion of bullets that open with a strong action verb."""
    bullets = _bullet_lines(experience_and_projects_text)

    if not bullets:
        return CheckResult(
            key="action_verbs",
            name="Action Verbs",
            score=0.0,
            weight=CATEGORY_WEIGHTS["action_verbs"],
            message="No bullet points detected to evaluate for action verbs.",
        )

    strong_count = 0
    weak_count = 0
    for bullet in bullets:
        lower = bullet.lower()
        if any(lower.startswith(phrase) for phrase in WEAK_OPENING_PHRASES):
            weak_count += 1
            continue
        first_word = re.sub(r"[^a-z]", "", lower.split()[0]) if lower.split() else ""
        if first_word in ACTION_VERBS:
            strong_count += 1

    score = round((strong_count / len(bullets)) * 100, 1)

    if weak_count:
        message = (
            f"{strong_count}/{len(bullets)} bullets start with a strong action verb. "
            f"{weak_count} bullet(s) use passive phrasing like 'responsible for' — "
            "rewrite these to lead with what you did."
        )
    elif score < 60:
        message = (
            f"Only {strong_count}/{len(bullets)} bullets start with a strong action "
            "verb (e.g. 'Built', 'Led', 'Optimized'). Rewrite weaker openers."
        )
    else:
        message = f"{strong_count}/{len(bullets)} bullets open with strong action verbs."

    return CheckResult(
        key="action_verbs",
        name="Action Verbs",
        score=score,
        weight=CATEGORY_WEIGHTS["action_verbs"],
        message=message,
    )


def check_quantified_achievements(experience_and_projects_text: str) -> CheckResult:
    """Score the proportion of bullets that include a number/metric (%, counts, time saved, etc.)."""
    bullets = _bullet_lines(experience_and_projects_text)

    if not bullets:
        return CheckResult(
            key="quantified_achievements",
            name="Quantified Achievements",
            score=0.0,
            weight=CATEGORY_WEIGHTS["quantified_achievements"],
            message="No bullet points detected to evaluate for quantifiable impact.",
        )

    quantified = sum(1 for b in bullets if _NUMBER_OR_PERCENT_RE.search(b))
    score = round((quantified / len(bullets)) * 100, 1)

    if quantified == 0:
        message = (
            "No bullets include numbers or metrics. Quantify impact where "
            "possible (e.g. 'reduced load time by 30%', 'led a team of 4')."
        )
    elif score < 40:
        message = f"Only {quantified}/{len(bullets)} bullets are quantified. Add metrics to more achievements."
    else:
        message = f"{quantified}/{len(bullets)} bullets include quantifiable impact — good practice."

    return CheckResult(
        key="quantified_achievements",
        name="Quantified Achievements",
        score=score,
        weight=CATEGORY_WEIGHTS["quantified_achievements"],
        message=message,
    )
