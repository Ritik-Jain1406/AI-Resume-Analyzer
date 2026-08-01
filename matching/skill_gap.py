"""
matching/skill_gap.py
------------------------
Phase 6: takes the missing skills identified by Phase 5's job matcher
and turns them into a prioritized, actionable learning plan.

Priority is a heuristic score combining three signals for each missing
skill, since most job descriptions only mention a given skill once and
frequency alone doesn't differentiate much:

  1. Position — a skill mentioned early in the JD (first ~40%) is scored
     higher, since requirements are conventionally front-loaded.
  2. Frequency — a skill mentioned more than once is scored higher.
  3. Category — core technical categories (Programming, Frameworks,
     Databases) outweigh secondary ones (Cloud, Developer Tools), which
     outweigh Soft Skills.

The combined score is bucketed into High / Medium / Low Priority tiers.
"""

from __future__ import annotations

import re

from matching.learning_resources import (
    CORE_CATEGORIES,
    SECONDARY_CATEGORIES,
    format_time_estimate,
    get_resource,
)
from matching.schemas import LearningPlan, SkillGapItem
from parser.skill_extractor import load_skills_db, normalize_skill_text
from utils.logger import get_logger

logger = get_logger(__name__)

# Score thresholds (max possible score is 6: position 0-2 + frequency 0-2 + category 0-2)
HIGH_PRIORITY_THRESHOLD = 4
MEDIUM_PRIORITY_THRESHOLD = 2

PRIORITY_ORDER = {"High Priority": 0, "Medium Priority": 1, "Low Priority": 2}


def _find_mention_positions(skill_norm: str, normalized_jd_text: str) -> list[int]:
    """Return character offsets of every mention of `skill_norm` in the normalized JD text."""
    if not skill_norm:
        return []
    pattern = rf"(?<![a-z0-9]){re.escape(skill_norm)}(?![a-z0-9])"
    return [m.start() for m in re.finditer(pattern, normalized_jd_text)]


def _priority_score(category: str, mention_count: int, first_position_ratio: float) -> int:
    position_score = 2 if first_position_ratio <= 0.4 else (1 if first_position_ratio <= 0.7 else 0)
    frequency_score = min(max(mention_count - 1, 0), 2)
    if category in CORE_CATEGORIES:
        category_score = 2
    elif category in SECONDARY_CATEGORIES:
        category_score = 1
    else:
        category_score = 0
    return position_score + frequency_score + category_score


def _score_to_priority(score: int) -> str:
    if score >= HIGH_PRIORITY_THRESHOLD:
        return "High Priority"
    if score >= MEDIUM_PRIORITY_THRESHOLD:
        return "Medium Priority"
    return "Low Priority"


def _build_roadmap(items: list[SkillGapItem]) -> list[str]:
    """Group prioritized items into a readable, phase-by-phase roadmap."""
    if not items:
        return ["No skill gaps detected — this resume already covers the job description well."]

    roadmap: list[str] = []
    phase_num = 1
    for tier in ("High Priority", "Medium Priority", "Low Priority"):
        tier_items = [i for i in items if i.priority == tier]
        if not tier_items:
            continue
        skill_list = ", ".join(f"{i.skill} ({i.estimated_time})" for i in tier_items)
        roadmap.append(f"Phase {phase_num} — {tier}: {skill_list}")
        phase_num += 1
    return roadmap


def analyze_skill_gap(missing_skills: list[str], jd_text: str) -> LearningPlan:
    """
    Build a prioritized learning plan for a list of missing skills.

    `missing_skills` should come from matching.job_matcher's MatchReport
    (skills present in the JD but not detected in the resume).
    `jd_text` is the raw job description text, used to score each skill's
    priority based on where/how often it's mentioned.
    """
    if not missing_skills:
        return LearningPlan(roadmap=_build_roadmap([]))

    db = load_skills_db()
    skill_to_category: dict[str, str] = (
        dict(zip(db["skill"], db["category"])) if not db.empty else {}
    )

    normalized_jd = normalize_skill_text(jd_text)
    jd_length = max(len(normalized_jd), 1)

    items: list[SkillGapItem] = []
    for skill in missing_skills:
        category = skill_to_category.get(skill, "Other")
        skill_norm = normalize_skill_text(skill)
        positions = _find_mention_positions(skill_norm, normalized_jd)
        mention_count = len(positions)
        first_position_ratio = (positions[0] / jd_length) if positions else 1.0

        score = _priority_score(category, mention_count, first_position_ratio)
        priority = _score_to_priority(score)

        resource_name, resource_url = get_resource(skill, category)

        items.append(
            SkillGapItem(
                skill=skill,
                category=category,
                priority=priority,
                mention_count=mention_count,
                estimated_time=format_time_estimate(category),
                resource_name=resource_name,
                resource_url=resource_url,
            )
        )

    items.sort(key=lambda i: (PRIORITY_ORDER[i.priority], -i.mention_count, i.skill))

    logger.info(
        "Skill gap analysis: {} missing skill(s), {} high priority",
        len(items),
        sum(1 for i in items if i.priority == "High Priority"),
    )

    return LearningPlan(
        gap_items=items,
        roadmap=_build_roadmap(items),
        total_missing=len(items),
        high_priority_count=sum(1 for i in items if i.priority == "High Priority"),
        medium_priority_count=sum(1 for i in items if i.priority == "Medium Priority"),
        low_priority_count=sum(1 for i in items if i.priority == "Low Priority"),
    )
