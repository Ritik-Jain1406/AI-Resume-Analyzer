"""
ats/scoring_rules.py
-----------------------
Static scoring configuration for Phase 4: category weights, action-verb
lists, and length thresholds. Kept separate from ats_score.py so the
scoring "policy" can be tuned without touching the checking logic.

Weights are fractions of the overall 0-100 ATS score and must sum to 1.0.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Category weights (must sum to 1.0)
# --------------------------------------------------------------------------- #
CATEGORY_WEIGHTS: dict[str, float] = {
    "contact_details": 0.10,
    "section_coverage": 0.20,
    "resume_length": 0.10,
    "keyword_richness": 0.20,
    "bullet_usage": 0.15,
    "action_verbs": 0.15,
    "quantified_achievements": 0.10,
}

assert abs(sum(CATEGORY_WEIGHTS.values()) - 1.0) < 1e-6, "CATEGORY_WEIGHTS must sum to 1.0"


# --------------------------------------------------------------------------- #
# Resume length thresholds (in words)
# --------------------------------------------------------------------------- #
ABS_MIN_WORDS = 150   # below this, the resume is almost certainly incomplete
IDEAL_MIN_WORDS = 350  # roughly a solid single-page resume
IDEAL_MAX_WORDS = 800  # roughly a full two-page resume
ABS_MAX_WORDS = 1200  # beyond this, ATS parsers and recruiters both struggle


# --------------------------------------------------------------------------- #
# Contact field weights (must sum to 100)
# --------------------------------------------------------------------------- #
CONTACT_FIELD_WEIGHTS: dict[str, int] = {
    "name": 30,
    "email": 30,
    "phone": 20,
    "linkedin": 10,
    "github": 10,
}


# --------------------------------------------------------------------------- #
# Keyword / skill richness tiers: (min_skill_count, score)
# --------------------------------------------------------------------------- #
SKILL_COUNT_SCORE_TIERS: list[tuple[int, float]] = [
    (13, 100.0),
    (8, 85.0),
    (4, 65.0),
    (1, 40.0),
    (0, 0.0),
]


# --------------------------------------------------------------------------- #
# Action verbs (strong, resume-appropriate) — first word of a bullet
# matching one of these (case-insensitive) counts as a strong opener.
# --------------------------------------------------------------------------- #
ACTION_VERBS: frozenset[str] = frozenset({
    "achieved", "administered", "analyzed", "architected", "automated",
    "authored", "boosted", "budgeted", "built", "coordinated",
    "collaborated", "conducted", "constructed", "consolidated",
    "contributed", "created", "delivered", "demonstrated", "deployed",
    "designed", "developed", "devised", "directed", "drove", "engineered",
    "enhanced", "established", "executed", "expanded", "expedited",
    "facilitated", "formulated", "founded", "generated", "guided",
    "headed", "identified", "implemented", "improved", "increased",
    "influenced", "initiated", "innovated", "integrated", "introduced",
    "launched", "led", "maintained", "managed", "mentored", "migrated",
    "modernized", "negotiated", "optimized", "organized", "orchestrated",
    "oversaw", "pioneered", "planned", "presented", "prioritized",
    "produced", "programmed", "reduced", "refactored", "researched",
    "resolved", "restructured", "revamped", "reviewed", "scaled",
    "spearheaded", "streamlined", "strengthened", "supervised",
    "supported", "tested", "trained", "transformed", "upgraded",
    "utilized", "validated", "won",
})

# Weak/passive phrases — a bullet opening with one of these is flagged as
# a weaker construction that ATS/recruiter parsers value less.
WEAK_OPENING_PHRASES: tuple[str, ...] = (
    "responsible for", "worked on", "helped with", "duties included",
    "in charge of", "tasked with", "assisted with", "was involved in",
)
