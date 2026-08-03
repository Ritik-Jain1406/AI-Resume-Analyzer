"""
app.py
------
Streamlit entry point for the AI Resume Analyzer.

Phase 1 wired up the app shell, sidebar navigation, config, and logging.
Phase 2 adds a real Resume Upload page backed by parser/resume_parser.py.
Remaining pages are still placeholders for later phases (ATS scoring,
matching, etc.).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import streamlit as st

from ai.action_verb_reference import ACTION_VERB_CATEGORIES
from ai.gemini_service import GeminiServiceError, is_configured
from ai.recommendation import generate_resume_suggestions
from ai.schemas import AIResumeSuggestions
from ats.ats_score import generate_ats_report
from ats.schemas import ATSReport
from config import settings, ensure_directories
from matching.job_matcher import compute_job_match
from matching.schemas import LearningPlan, MatchReport
from matching.skill_gap import analyze_skill_gap
from parser.resume_parser import parse_resume
from parser.schemas import ParsedResume, SkillExtractionResult
from parser.skill_extractor import extract_skills
from utils.logger import get_logger
from utils.validators import ValidationError, validate_file_size
from visualization.dashboard import render_dashboard as render_dashboard_layout

logger = get_logger(__name__)

PAGES: list[str] = [
    "Home",
    "Resume Upload",
    "ATS Analysis",
    "Job Matching",
    "Skill Gap",
    "AI Suggestions",
    "Interview Prep",
    "Dashboard",
    "History",
    "About",
]


def render_home() -> None:
    st.title(f"📄 {settings.app_name}")
    st.write(
        "Upload a resume to check ATS compatibility, match it against a "
        "job description, and get AI-powered improvement suggestions."
    )
    st.info(
        "This is the Phase 1 project scaffold. Parsing, scoring, and "
        "matching logic will be added in later phases.",
        icon="🛠️",
    )

    with st.expander("Environment check"):
        st.write(
            {
                "app_env": settings.app_env,
                "debug": settings.debug,
                "log_level": settings.log_level,
                "database_url": settings.database_url,
                "semantic_model_name": settings.semantic_model_name,
            }
        )


def render_resume_upload() -> None:
    st.title("📤 Resume Upload")
    st.write(
        "Upload a PDF or DOCX resume to extract contact details and "
        "section content. This becomes the input for ATS scoring, job "
        "matching, and every later phase."
    )

    uploaded_file = st.file_uploader(
        "Choose a resume file",
        type=["pdf", "docx"],
        accept_multiple_files=False,
    )

    if uploaded_file is None:
        if "parsed_resume" in st.session_state:
            st.caption("Showing the most recently parsed resume below.")
        else:
            return

    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        try:
            validate_file_size(len(file_bytes))
        except ValidationError as exc:
            st.error(str(exc))
            return

        suffix = Path(uploaded_file.name).suffix.lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            with st.spinner("Parsing resume..."):
                parsed = parse_resume(tmp_path, original_filename=uploaded_file.name)
        except ValidationError as exc:
            st.error(str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected error parsing {}", uploaded_file.name)
            st.error(f"Something went wrong while parsing this file: {exc}")
            return
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        st.session_state["parsed_resume"] = parsed
        st.success(f"Parsed '{uploaded_file.name}' successfully.")

    parsed: ParsedResume | None = st.session_state.get("parsed_resume")
    if parsed is None:
        return

    if parsed.parsing_warnings:
        for warning in parsed.parsing_warnings:
            st.warning(warning, icon="⚠️")

    st.subheader("Contact Information")
    contact = parsed.contact
    cols = st.columns(3)
    cols[0].metric("Name", contact.name or "Not found")
    cols[1].metric("Email", contact.email or "Not found")
    cols[2].metric("Phone", contact.phone or "Not found")

    link_cols = st.columns(3)
    link_cols[0].write(f"**LinkedIn:** {contact.linkedin or '_Not found_'}")
    link_cols[1].write(f"**GitHub:** {contact.github or '_Not found_'}")
    link_cols[2].write(f"**Portfolio:** {contact.portfolio or '_Not found_'}")

    st.subheader("Detected Sections")
    if parsed.detected_section_order:
        st.write(" → ".join(s.title() for s in parsed.detected_section_order))
    else:
        st.caption("No section headings were confidently detected.")

    section_fields = parsed.sections.model_dump()
    for section_name, content in section_fields.items():
        with st.expander(section_name.title(), expanded=False):
            if content:
                st.text(content)
            else:
                st.caption("Not detected in this resume.")

    st.subheader("🧠 Detected Skills")
    skill_result = extract_skills(parsed.cleaned_text)
    st.session_state["skill_extraction"] = skill_result

    if not skill_result.all_detected:
        st.info(
            "No known skills were detected against our skills database. "
            "Consider adding a dedicated Skills section listing your "
            "tools and technologies."
        )
    else:
        detected_categories = sum(
            1 for skills in skill_result.detected_by_category.values() if skills
        )
        st.write(
            f"**{len(skill_result.all_detected)} skill(s) detected** "
            f"across {detected_categories} categor{'y' if detected_categories == 1 else 'ies'}."
        )
        for category in skill_result.all_known_categories:
            detected = skill_result.detected_by_category.get(category, [])
            missing = skill_result.missing_by_category.get(category, [])
            if not detected and not missing:
                continue
            with st.expander(f"{category} — {len(detected)} detected", expanded=bool(detected)):
                if detected:
                    st.markdown(
                        "**Detected:** " + " ".join(f"`{s}`" for s in detected)
                    )
                else:
                    st.caption("None detected in this category.")
                if missing:
                    st.caption(
                        "Other known skills in this category (not detected): "
                        + ", ".join(missing)
                    )
        st.caption(
            "This compares against our general skills database. Matching "
            "against a specific job description comes in Job Matching / "
            "Skill Gap."
        )

    st.subheader("Structured Output (JSON)")
    combined_output = {
        **parsed.model_dump(),
        "skill_extraction": skill_result.model_dump(),
    }
    st.json(combined_output)

    st.download_button(
        "Download parsed JSON",
        data=json.dumps(combined_output, indent=2, default=str),
        file_name=f"{Path(parsed.source_filename).stem}_parsed.json",
        mime="application/json",
    )


def render_ats_analysis() -> None:
    st.title("✅ ATS Analysis")

    parsed: ParsedResume | None = st.session_state.get("parsed_resume")
    if parsed is None:
        st.info("Upload a resume on the **Resume Upload** page first.", icon="📤")
        return

    skill_result: SkillExtractionResult | None = st.session_state.get("skill_extraction")
    if skill_result is None:
        skill_result = extract_skills(parsed.cleaned_text)
        st.session_state["skill_extraction"] = skill_result

    report = generate_ats_report(parsed, skill_result)

    score_col, status_col = st.columns([2, 1])
    with score_col:
        st.metric("Overall ATS Score", f"{report.overall_score:.1f} / 100")
        st.progress(min(report.overall_score, 100) / 100)
    with status_col:
        if report.passed:
            st.success(f"Meets the {settings.ats_pass_threshold}/100 pass threshold", icon="✅")
        else:
            st.error(f"Below the {settings.ats_pass_threshold}/100 pass threshold", icon="⚠️")
        st.caption(f"Based on {report.resume_word_count} words analyzed.")

    st.subheader("Section-wise Breakdown")
    for check in sorted(report.checks, key=lambda c: c.weight, reverse=True):
        st.write(f"**{check.name}** — {check.score:.0f}/100  ·  weight {check.weight * 100:.0f}%")
        st.progress(min(check.score, 100) / 100)
        st.caption(check.message)

    st.subheader("Top Suggestions")
    if not report.suggestions:
        st.success("No major issues found — this resume looks ATS-ready!")
    else:
        for i, suggestion in enumerate(report.suggestions, start=1):
            st.markdown(f"{i}. {suggestion}")

    st.download_button(
        "Download ATS report (JSON)",
        data=json.dumps(report.model_dump(), indent=2, default=str),
        file_name=f"{Path(parsed.source_filename).stem}_ats_report.json",
        mime="application/json",
    )


def render_job_matching() -> None:
    st.title("🎯 Job Matching")

    parsed: ParsedResume | None = st.session_state.get("parsed_resume")
    if parsed is None:
        st.info("Upload a resume on the **Resume Upload** page first.", icon="📤")
        return

    st.write("Paste a job description below to see how well your resume matches it.")

    jd_text = st.text_area(
        "Job description",
        height=250,
        placeholder="Paste the full job description here...",
        key="jd_text_input",
    )

    uploaded_jd = st.file_uploader("...or upload a .txt file instead", type=["txt"])
    if uploaded_jd is not None:
        jd_text = uploaded_jd.getvalue().decode("utf-8", errors="ignore")
        st.caption(f"Using uploaded file: {uploaded_jd.name}")

    analyze_clicked = st.button("Analyze Match", type="primary", disabled=not jd_text.strip())

    if analyze_clicked:
        with st.spinner("Computing match (first run may download the semantic model)..."):
            report = compute_job_match(parsed.cleaned_text, jd_text)
        st.session_state["match_report"] = report

    report: MatchReport | None = st.session_state.get("match_report")
    if report is None:
        return

    for warning in report.warnings:
        st.warning(warning, icon="⚠️")

    score_col, meta_col = st.columns([2, 1])
    with score_col:
        st.metric("Overall Match", f"{report.overall_match_percent:.1f}%")
        st.progress(min(report.overall_match_percent, 100) / 100)
    with meta_col:
        st.caption(f"Job description: {report.jd_word_count} words")

    st.subheader("Match Signals")
    sig_cols = st.columns(4)
    sig_cols[0].metric(
        "Semantic Similarity",
        f"{report.semantic_similarity:.1f}%" if report.semantic_available else "N/A",
    )
    sig_cols[1].metric("Cosine Similarity", f"{report.cosine_similarity:.1f}%")
    sig_cols[2].metric("Keyword Coverage", f"{report.keyword_coverage:.1f}%")
    sig_cols[3].metric("Skill Match", f"{report.skill_match_percent:.1f}%")

    st.subheader("Skills")
    skill_col1, skill_col2 = st.columns(2)
    with skill_col1:
        st.markdown(f"**✅ Matched ({len(report.matched_skills)})**")
        if report.matched_skills:
            st.markdown(" ".join(f"`{s}`" for s in report.matched_skills))
        else:
            st.caption("None matched.")
    with skill_col2:
        st.markdown(f"**❌ Missing ({len(report.missing_skills)})**")
        if report.missing_skills:
            st.markdown(" ".join(f"`{s}`" for s in report.missing_skills))
        else:
            st.caption("None — every JD skill was found in the resume.")

    st.subheader("Keyword Coverage")
    kw_col1, kw_col2 = st.columns(2)
    with kw_col1:
        st.markdown(f"**✅ Matched ({len(report.matched_keywords)})**")
        st.caption(", ".join(report.matched_keywords) or "None matched.")
    with kw_col2:
        st.markdown(f"**❌ Missing ({len(report.missing_keywords)})**")
        st.caption(", ".join(report.missing_keywords) or "None missing.")

    st.download_button(
        "Download match report (JSON)",
        data=json.dumps(report.model_dump(), indent=2, default=str),
        file_name=f"{Path(parsed.source_filename).stem}_match_report.json",
        mime="application/json",
    )


def render_skill_gap() -> None:
    st.title("📈 Skill Gap Analysis")

    parsed: ParsedResume | None = st.session_state.get("parsed_resume")
    if parsed is None:
        st.info("Upload a resume on the **Resume Upload** page first.", icon="📤")
        return

    match_report: MatchReport | None = st.session_state.get("match_report")
    if match_report is None:
        st.info(
            "Run a match on the **Job Matching** page first — skill gaps "
            "are calculated against a specific job description.",
            icon="🎯",
        )
        return

    jd_text = st.session_state.get("jd_text_input", "") or ""

    if not match_report.missing_skills:
        st.success(
            "No missing skills detected — this resume already covers every "
            "skill found in the job description!",
            icon="✅",
        )
        return

    plan: LearningPlan = analyze_skill_gap(match_report.missing_skills, jd_text)
    st.session_state["learning_plan"] = plan

    count_cols = st.columns(3)
    count_cols[0].metric("High Priority", plan.high_priority_count)
    count_cols[1].metric("Medium Priority", plan.medium_priority_count)
    count_cols[2].metric("Low Priority", plan.low_priority_count)

    st.subheader("Suggested Roadmap")
    for step in plan.roadmap:
        st.markdown(f"- {step}")

    st.subheader("Skill-by-Skill Breakdown")
    priority_icons = {"High Priority": "🔴", "Medium Priority": "🟡", "Low Priority": "🟢"}
    for item in plan.gap_items:
        icon = priority_icons.get(item.priority, "•")
        with st.expander(f"{icon} {item.skill} — {item.priority}"):
            st.write(f"**Category:** {item.category}")
            st.write(f"**Estimated time to learn:** {item.estimated_time}")
            st.write(f"**Mentioned in JD:** {item.mention_count} time(s)")
            st.markdown(f"**Resource:** [{item.resource_name}]({item.resource_url})")

    st.download_button(
        "Download learning plan (JSON)",
        data=json.dumps(plan.model_dump(), indent=2, default=str),
        file_name=f"{Path(parsed.source_filename).stem}_learning_plan.json",
        mime="application/json",
    )


def render_ai_suggestions() -> None:
    st.title("🤖 AI Resume Suggestions")

    parsed: ParsedResume | None = st.session_state.get("parsed_resume")
    if parsed is None:
        st.info("Upload a resume on the **Resume Upload** page first.", icon="📤")
        return

    if not is_configured():
        st.warning(
            "Gemini API key is not configured. Add GEMINI_API_KEY to your local "
            ".env file to use AI Resume Suggestions.",
            icon="🔑",
        )
        return

    skill_result: SkillExtractionResult | None = st.session_state.get("skill_extraction")
    if skill_result is None:
        skill_result = extract_skills(parsed.cleaned_text)
        st.session_state["skill_extraction"] = skill_result

    ats_report: ATSReport = generate_ats_report(parsed, skill_result)
    match_report: MatchReport | None = st.session_state.get("match_report")
    learning_plan: LearningPlan | None = st.session_state.get("learning_plan")

    if match_report is not None:
        st.caption(
            "✅ Job description results detected — job-specific suggestions will be included."
        )
    else:
        st.caption(
            "ℹ️ No job description analyzed yet. Run **Job Matching** first for "
            "job-specific suggestions, or generate general suggestions now."
        )

    target_role = st.text_input(
        "Target role (optional)",
        placeholder="e.g. Backend Software Engineer",
        key="ai_target_role",
    )

    has_existing = "ai_suggestions" in st.session_state
    button_label = "Regenerate Suggestions" if has_existing else "Generate Suggestions"

    if st.button(button_label, type="primary"):
        try:
            with st.spinner("Generating AI suggestions with Gemini..."):
                suggestions = generate_resume_suggestions(
                    parsed=parsed,
                    skill_result=skill_result,
                    ats_report=ats_report,
                    target_role=target_role,
                    match_report=match_report,
                    learning_plan=learning_plan,
                )
            st.session_state["ai_suggestions"] = suggestions
        except GeminiServiceError as exc:
            # These messages are pre-validated as safe to show directly — never
            # wrap them in additional detail that might leak internals.
            st.error(str(exc))

    suggestions: AIResumeSuggestions | None = st.session_state.get("ai_suggestions")

    st.subheader("Stronger Action Verbs (reference)")
    verb_cols = st.columns(len(ACTION_VERB_CATEGORIES))
    for col, (category, verbs) in zip(verb_cols, ACTION_VERB_CATEGORIES.items()):
        with col:
            st.markdown(f"**{category}**")
            for verb in verbs:
                st.caption(verb)

    if suggestions is None:
        return

    st.divider()

    if suggestions.weaknesses:
        st.subheader("Overall AI Recommendations")
        priority_icons = {"High Priority": "🔴", "Medium Priority": "🟡", "Low Priority": "🟢"}
        for tier in ("High Priority", "Medium Priority", "Low Priority"):
            tier_items = [w for w in suggestions.weaknesses if w.priority == tier]
            if not tier_items:
                continue
            st.markdown(f"**{priority_icons.get(tier, '•')} {tier}**")
            for item in tier_items:
                st.markdown(f"- **{item.issue}** — {item.recommendation}")

    if suggestions.summary is not None:
        st.subheader("Improve Your Summary")
        st.markdown("**Original:**")
        st.caption(suggestions.summary.original or "_No summary detected in the resume._")
        st.markdown("**AI Improved Version:**")
        st.write(suggestions.summary.improved or "_Not generated._")
        with st.expander("More versions"):
            st.markdown("**Concise version:**")
            st.write(suggestions.summary.concise or "_Not generated._")
            if suggestions.summary.target_role_focused:
                st.markdown("**Target-role-focused version:**")
                st.write(suggestions.summary.target_role_focused)

    if suggestions.experience:
        st.subheader("Experience Improvements")
        for i, item in enumerate(suggestions.experience, start=1):
            with st.expander(f"Bullet {i}: {item.original[:60]}..."):
                st.markdown("**Original:**")
                st.caption(item.original)
                st.markdown("**Improved:**")
                st.write(item.improved)
                if item.reason:
                    st.markdown("**Why:**")
                    st.caption(item.reason)

    if suggestions.projects:
        st.subheader("Project Improvements")
        for project in suggestions.projects:
            with st.expander(project.project_name):
                st.markdown("**Original:**")
                st.caption(project.original or "_Not provided._")
                if project.improved_bullets:
                    st.markdown("**Improved bullets:**")
                    for bullet in project.improved_bullets:
                        st.markdown(f"- {bullet}")
                if project.technologies:
                    st.markdown("**Technologies:** " + ", ".join(f"`{t}`" for t in project.technologies))
                if project.action_verbs:
                    st.markdown("**Suggested action verbs:** " + ", ".join(project.action_verbs))
                if project.suggestions:
                    st.markdown("**Suggestions:**")
                    for s in project.suggestions:
                        st.markdown(f"- {s}")

    if match_report is not None and suggestions.job_specific_suggestions:
        st.subheader("Job-Specific Suggestions")
        grouped: dict[str, list[str]] = {"Already Strong": [], "Improve": [], "Missing": []}
        for item in suggestions.job_specific_suggestions:
            grouped.setdefault(item.category, []).append(item.detail)
        for category, details in grouped.items():
            if not details:
                continue
            st.markdown(f"**{category}**")
            for d in details:
                st.markdown(f"- {d}")

    st.download_button(
        "Download AI suggestions (JSON)",
        data=json.dumps(suggestions.model_dump(), indent=2, default=str),
        file_name=f"{Path(parsed.source_filename).stem}_ai_suggestions.json",
        mime="application/json",
    )


def render_dashboard_page() -> None:
    st.title("📊 Dashboard")

    parsed: ParsedResume | None = st.session_state.get("parsed_resume")
    if parsed is None:
        st.info("Upload a resume on the **Resume Upload** page first.", icon="📤")
        return

    # ATS is cheap/deterministic, so — same as the ATS Analysis page — it's
    # safe to (re)compute fresh here. Everything else is read-only from
    # session state: the dashboard never triggers semantic matching or Gemini.
    skill_result: SkillExtractionResult | None = st.session_state.get("skill_extraction")
    if skill_result is None:
        skill_result = extract_skills(parsed.cleaned_text)
        st.session_state["skill_extraction"] = skill_result

    ats_report = generate_ats_report(parsed, skill_result)
    match_report: MatchReport | None = st.session_state.get("match_report")
    learning_plan: LearningPlan | None = st.session_state.get("learning_plan")
    ai_suggestions: AIResumeSuggestions | None = st.session_state.get("ai_suggestions")

    render_dashboard_layout(
        parsed=parsed,
        ats_report=ats_report,
        skill_result=skill_result,
        match_report=match_report,
        learning_plan=learning_plan,
        ai_suggestions=ai_suggestions,
    )


def render_placeholder(page_name: str) -> None:
    st.title(page_name)
    st.warning(f"'{page_name}' isn't implemented yet — coming in a later phase.")


def main() -> None:
    st.set_page_config(
        page_title=settings.app_name,
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    ensure_directories()
    logger.info("App started", app_env=settings.app_env)

    st.sidebar.title("Navigation")
    selected_page = st.sidebar.radio("Go to", PAGES, label_visibility="collapsed")

    if selected_page == "Home":
        render_home()
    elif selected_page == "Resume Upload":
        render_resume_upload()
    elif selected_page == "ATS Analysis":
        render_ats_analysis()
    elif selected_page == "Job Matching":
        render_job_matching()
    elif selected_page == "Skill Gap":
        render_skill_gap()
    elif selected_page == "AI Suggestions":
        render_ai_suggestions()
    elif selected_page == "Dashboard":
        render_dashboard_page()
    else:
        render_placeholder(selected_page)


if __name__ == "__main__":
    main()
