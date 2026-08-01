"""
parser/skill_extractor.py
----------------------------
Phase 3: extracts skills mentioned in resume text against the
maintained skills database (data/skills.csv), categorized into
Programming / Frameworks / Cloud / Databases / Developer Tools /
Soft Skills.

Matching strategy:
  1. Alias expansion — common shorthand ("JS", "ReactJS", "Postgres",
     "K8s") is normalized to the canonical name in the skills DB before
     matching, so both forms are recognized.
  2. Exact match — word-boundary regex match of each known skill
     against the normalized text. Handles the vast majority of cases
     reliably with no false positives.
  3. Fuzzy fallback — for single-token skills only (multi-word fuzzy
     matching against free text is too noisy), rapidfuzz catches close
     variants/typos ("Reakt" -> "React") that exact matching would miss.

The skills DB is cached in memory after first load — call
`load_skills_db.cache_clear()` if data/skills.csv changes at runtime
(e.g. an admin feature edits it later).
"""

from __future__ import annotations

import re
from functools import lru_cache

import pandas as pd
from rapidfuzz import fuzz, process

from config import settings
from parser.schemas import SkillExtractionResult
from utils.logger import get_logger

logger = get_logger(__name__)

# Common shorthand/variant spellings -> canonical name as it appears in skills.csv.
# Keys and values are matched/inserted in already-normalized (lowercase) form.
SKILL_ALIASES: dict[str, str] = {
    "js": "javascript",
    "reactjs": "react",
    "react.js": "react",
    "nodejs": "node.js",
    "node js": "node.js",
    "vuejs": "vue.js",
    "vue": "vue.js",
    "nextjs": "next.js",
    "expressjs": "express.js",
    "postgres": "postgresql",
    "py": "python",
    "golang": "go",
    "k8s": "kubernetes",
    "ci cd": "ci/cd",
    "cicd": "ci/cd",
    "dotnet": ".net",
    "asp.net": ".net",
    "sklearn": "scikit-learn",
    "vscode": "vs code",
    "visual studio code": "vs code",
    "rails": "ruby on rails",
    "tailwind": "tailwind css",
}

# rapidfuzz similarity score (0-100) required to accept a fuzzy match.
# Kept high to avoid false positives — this is a fallback, not the primary path.
FUZZY_MATCH_THRESHOLD = 88

# Skills shorter than this are excluded from fuzzy matching — fuzzy scores
# on very short strings are unreliable (e.g. "R" fuzzy-matches almost anything).
MIN_FUZZY_SKILL_LENGTH = 3


@lru_cache(maxsize=1)
def load_skills_db() -> pd.DataFrame:
    """Load and cache the skills database from data/skills.csv."""
    path = settings.skills_csv
    if not path.exists():
        logger.error("Skills database not found at {}", path)
        return pd.DataFrame(columns=["skill", "category"])

    df = pd.read_csv(path)
    df["skill"] = df["skill"].astype(str).str.strip()
    df["category"] = df["category"].astype(str).str.strip()
    return df


def normalize_skill_text(text: str) -> str:
    """
    Lowercase and strip everything except characters that appear in skill
    names. Public so other modules (e.g. matching.skill_gap) can apply the
    exact same normalization rules when matching skill names against text.
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9+./#\s-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# Kept as a private alias so existing calls within this module are unaffected.
_normalize = normalize_skill_text


def _expand_aliases(normalized_text: str) -> str:
    """Rewrite known shorthand in the text to each skill's canonical form."""
    for alias, canonical in SKILL_ALIASES.items():
        pattern = rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"
        normalized_text = re.sub(pattern, canonical, normalized_text)
    return normalized_text


def _exact_match(normalized_text: str, skill_norm: str) -> bool:
    pattern = rf"(?<![a-z0-9]){re.escape(skill_norm)}(?![a-z0-9])"
    return re.search(pattern, normalized_text) is not None


def extract_skills(text: str) -> SkillExtractionResult:
    """
    Extract known skills from `text`, categorized by the skills database.

    `text` should already be cleaned (see parser.text_cleaner.clean_text).
    Pass the resume's full cleaned text (not just the Skills section) for
    best recall — skills are often mentioned in Experience/Projects too.
    """
    db = load_skills_db()
    if db.empty or not text.strip():
        return SkillExtractionResult()

    normalized_text = _expand_aliases(_normalize(text))
    text_tokens = set(normalized_text.split())

    detected: set[str] = set()

    # Pass 1: exact match
    for _, row in db.iterrows():
        skill_norm = _normalize(row["skill"])
        if _exact_match(normalized_text, skill_norm):
            detected.add(row["skill"])

    # Pass 2: fuzzy fallback for single-token skills not already found
    remaining = db[~db["skill"].isin(detected)]
    for _, row in remaining.iterrows():
        skill = row["skill"]
        skill_norm = _normalize(skill)
        if " " in skill_norm or len(skill_norm) < MIN_FUZZY_SKILL_LENGTH:
            continue
        match = process.extractOne(skill_norm, text_tokens, scorer=fuzz.ratio)
        if match and match[1] >= FUZZY_MATCH_THRESHOLD:
            detected.add(skill)

    detected_by_category: dict[str, list[str]] = {}
    missing_by_category: dict[str, list[str]] = {}
    for category, group in db.groupby("category"):
        cat_skills = list(group["skill"])
        detected_by_category[category] = sorted(s for s in cat_skills if s in detected)
        missing_by_category[category] = sorted(s for s in cat_skills if s not in detected)

    logger.info("Skill extraction found {} skill(s)", len(detected))

    return SkillExtractionResult(
        detected_by_category=detected_by_category,
        missing_by_category=missing_by_category,
        all_detected=sorted(detected),
        all_known_categories=sorted(db["category"].unique().tolist()),
    )
