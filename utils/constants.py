"""
utils/constants.py
-------------------
Static, project-wide constants that don't belong in config.py (which is
for *configurable* settings). Things like fixed labels, regex patterns,
and enums used across multiple modules live here.
"""

from __future__ import annotations

# --- Resume sections we attempt to detect (Phase 2) ---
RESUME_SECTIONS: list[str] = [
    "summary",
    "education",
    "experience",
    "projects",
    "skills",
    "certifications",
    "achievements",
]

# --- Contact info regex patterns (Phase 2) ---
EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
PHONE_REGEX = r"(\+?\d{1,3}[-.\s]?)?\(?\d{3,4}\)?[-.\s]?\d{3}[-.\s]?\d{3,4}"
LINKEDIN_REGEX = r"(https?://)?(www\.)?linkedin\.com/in/[A-Za-z0-9_-]+/?"
GITHUB_REGEX = r"(https?://)?(www\.)?github\.com/[A-Za-z0-9_-]+/?"

# --- Skill priority levels (Phase 6) ---
class SkillPriority:
    HIGH = "High Priority"
    MEDIUM = "Medium Priority"
    LOW = "Low Priority"

# --- Interview question difficulty levels (Phase 10) ---
class DifficultyLevel:
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"

# --- Supported upload types ---
SUPPORTED_EXTENSIONS: tuple[str, ...] = (".pdf", ".docx")
