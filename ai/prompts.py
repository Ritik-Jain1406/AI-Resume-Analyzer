"""
ai/prompts.py
----------------
Prompt construction for Phase 7. Kept separate from gemini_service.py's
API call logic so wording can be iterated on independently.

Privacy note: build_suggestions_prompt() deliberately never includes
contact info (name, email, phone, LinkedIn/GitHub/portfolio links) —
none of it is needed to improve summary/bullet wording, so it's left out
to minimize what personal data leaves the app.
"""

from __future__ import annotations

from ats.schemas import ATSReport
from matching.schemas import LearningPlan, MatchReport
from parser.schemas import ParsedResume, SkillExtractionResult

SYSTEM_INSTRUCTION = """You are an experienced technical recruiter and professional resume editor.

Rules you must always follow:
- Improve clarity and impact using only the information provided in the user message.
- Never fabricate work experience, employers, job titles, dates, metrics, skills, or certifications.
- If a bullet lacks a measurable result, point out where a real metric could be added — never invent one.
- Only reference skills/technologies explicitly listed in the provided data — never introduce new ones.
- Prefer concise, professional, ATS-friendly language and strong action verbs.
- Do not keyword-stuff.
- Base every suggestion on the resume evidence given; if something isn't present, say so rather than guessing.
- For any skill you note as missing relative to a target job, phrase it as something to consider learning or
  demonstrating — never instruct the user to simply add it to their resume.
- Output must be a single JSON object matching exactly the schema described in the user message.
  No markdown code fences, no commentary before or after the JSON.
"""

RESPONSE_SCHEMA_DESCRIPTION = """
Respond with a single JSON object with exactly this shape:

{
  "summary": {
    "original": "<the resume's existing summary text, or null if none was found>",
    "improved": "<rewritten, stronger version of the summary>",
    "concise": "<a shorter 1-2 sentence version>",
    "target_role_focused": "<version tailored to the target role/job description, or null if none was given>"
  },
  "experience": [
    {"original": "<original bullet text, verbatim>", "improved": "<rewritten bullet>", "reason": "<short explanation of what changed and why>"}
  ],
  "projects": [
    {
      "project_name": "<project name as it appears in the resume>",
      "original": "<original project description text, verbatim>",
      "improved_bullets": ["<rewritten bullet>", "..."],
      "technologies": ["<only technologies explicitly present in the SKILLS DETECTED or project text below>"],
      "action_verbs": ["<strong action verbs relevant to this project>"],
      "suggestions": ["<e.g. where a real metric could be added>"]
    }
  ],
  "weaknesses": [
    {"priority": "High Priority" | "Medium Priority" | "Low Priority", "issue": "<short description>", "recommendation": "<actionable fix>"}
  ],
  "job_specific_suggestions": [
    {"category": "Already Strong" | "Improve" | "Missing", "detail": "<specific, concrete point>"}
  ]
}

Rules for filling this in:
- If the resume has no Experience section, return an empty "experience" list.
- If the resume has no Projects section, return an empty "projects" list.
- If no target role or job description was provided below, set "summary.target_role_focused" to null
  and return an empty "job_specific_suggestions" list.
- Base "weaknesses" on the ATS analysis and resume content given below; rank the most impactful issues first.
"""


def _section_or_placeholder(section_text: str | None) -> str:
    return section_text if section_text else "(none detected)"


def build_suggestions_prompt(
    parsed: ParsedResume,
    skill_result: SkillExtractionResult,
    ats_report: ATSReport,
    target_role: str = "",
    match_report: MatchReport | None = None,
    learning_plan: LearningPlan | None = None,
) -> str:
    """Build the full user-turn prompt sent to Gemini for AI Resume Suggestions."""
    sections = parsed.sections

    lines: list[str] = [
        "Analyze the following resume content and generate improvement suggestions.",
        "",
        f"TARGET ROLE: {target_role.strip() or '(not specified)'}",
        "",
        "=== SUMMARY (as written) ===",
        _section_or_placeholder(sections.summary),
        "",
        "=== EDUCATION ===",
        _section_or_placeholder(sections.education),
        "",
        "=== EXPERIENCE ===",
        _section_or_placeholder(sections.experience),
        "",
        "=== PROJECTS ===",
        _section_or_placeholder(sections.projects),
        "",
        "=== CERTIFICATIONS ===",
        _section_or_placeholder(sections.certifications),
        "",
        "=== ACHIEVEMENTS ===",
        _section_or_placeholder(sections.achievements),
        "",
        "=== SKILLS DETECTED (only reference these — do not invent others) ===",
        ", ".join(skill_result.all_detected) or "(none detected)",
        "",
        "=== EXISTING ATS ANALYSIS (for context on weak areas) ===",
        f"Overall ATS score: {ats_report.overall_score}/100",
    ]
    for check in ats_report.checks:
        lines.append(f"- {check.name}: {check.score}/100 — {check.message}")
    lines.append("")

    if match_report is not None:
        lines.extend([
            "=== JOB DESCRIPTION MATCH (existing analysis) ===",
            f"Overall match: {match_report.overall_match_percent}%",
            "Matched skills: " + (", ".join(match_report.matched_skills) or "(none)"),
            "Missing skills (present in job description, not in resume): "
            + (", ".join(match_report.missing_skills) or "(none)"),
            "Missing keywords: " + (", ".join(match_report.missing_keywords) or "(none)"),
            "",
        ])

    if learning_plan is not None and learning_plan.gap_items:
        lines.append("=== SKILL GAP PRIORITIES (existing analysis) ===")
        for item in learning_plan.gap_items:
            lines.append(f"- {item.skill} ({item.priority})")
        lines.append("")

    lines.append(RESPONSE_SCHEMA_DESCRIPTION)

    return "\n".join(lines)
