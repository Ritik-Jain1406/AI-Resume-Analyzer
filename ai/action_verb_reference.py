"""
ai/action_verb_reference.py
-------------------------------
Static, categorized action-verb reference (Phase 7 feature 4).

Deliberately kept as static data rather than a Gemini call: a general
"stronger verbs by category" cheat sheet isn't resume-specific, carries
zero hallucination risk, and doesn't need to burn an API call every time
someone views the page.
"""

ACTION_VERB_CATEGORIES: dict[str, list[str]] = {
    "Development": ["Developed", "Implemented", "Engineered", "Built", "Architected", "Programmed"],
    "Analysis": ["Analyzed", "Evaluated", "Investigated", "Assessed", "Diagnosed"],
    "Optimization": ["Optimized", "Improved", "Streamlined", "Refactored", "Enhanced"],
    "Leadership": ["Led", "Coordinated", "Managed", "Mentored", "Supervised", "Directed"],
    "Research": ["Investigated", "Designed", "Experimented", "Researched", "Explored"],
}
