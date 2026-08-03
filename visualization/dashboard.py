"""
visualization/dashboard.py
------------------------------
Phase 8: dashboard layout/composition. Arranges visualization/charts.py
outputs plus two small presentation-only summaries (pipeline overview,
AI suggestions summary card) into the Dashboard page.

Strictly presentation-only, per the Phase 8 spec:
- Every argument is data the caller (app.py) already has from session
  state, or a fresh call to the existing, cheap, deterministic
  generate_ats_report() — same as the ATS Analysis page already does.
- This module NEVER computes semantic similarity, calls Gemini, or
  invents a number that doesn't already exist on the models passed in.
- Job match / skill gap / AI suggestions sections are read-only: if the
  corresponding session-state object is absent, that section is grayed
  out with a prompt to visit the relevant page — never computed here.
"""

from __future__ import annotations

import json

import streamlit as st

from ai.schemas import AIResumeSuggestions
from ats.schemas import ATSReport
from matching.schemas import LearningPlan, MatchReport
from parser.schemas import ParsedResume, SkillExtractionResult
from visualization.charts import (
    ats_score_gauge,
    ats_weak_sections_bar,
    job_match_gauge,
    job_match_signals_bar,
    resume_strength_radar,
    skill_distribution_pie,
    skill_gap_priority_bar,
)

PIPELINE_STAGES: list[str] = [
    "Resume", "ATS", "Skills", "Job Match", "Skill Gap", "AI Suggestions",
]


def render_pipeline_overview(
    parsed: ParsedResume | None,
    ats_report: ATSReport | None,
    skill_result: SkillExtractionResult | None,
    match_report: MatchReport | None,
    learning_plan: LearningPlan | None,
    ai_suggestions: AIResumeSuggestions | None,
) -> None:
    """
    Compact visual of which pipeline stages already have data.
    Resume -> ATS -> Skills -> Job Match -> Skill Gap -> AI Suggestions.
    Purely reflects presence/absence of already-computed data — no logic.
    """
    completed = [
        parsed is not None,
        ats_report is not None,
        bool(skill_result and skill_result.all_detected),
        match_report is not None,
        learning_plan is not None,
        ai_suggestions is not None,
    ]
    cols = st.columns(len(PIPELINE_STAGES))
    for i, (col, stage, done) in enumerate(zip(cols, PIPELINE_STAGES, completed)):
        icon = "✅" if done else "⬜"
        with col:
            st.markdown(f"<div style='text-align:center'>{icon}<br/><small>{stage}</small></div>", unsafe_allow_html=True)
            if i < len(PIPELINE_STAGES) - 1:
                st.markdown("<div style='text-align:center;color:#bbb'>→</div>", unsafe_allow_html=True)


def render_ai_suggestions_summary(ai_suggestions: AIResumeSuggestions | None) -> None:
    """Small summary card over existing Phase 7 output. Never triggers generation."""
    st.subheader("AI Suggestions Summary")
    if ai_suggestions is None:
        st.info(
            "No AI suggestions generated yet. Visit **AI Suggestions** and click "
            "'Generate Suggestions' — this dashboard only displays existing results, "
            "it never calls Gemini itself.",
            icon="🤖",
        )
        return

    counts = {"High Priority": 0, "Medium Priority": 0, "Low Priority": 0}
    for w in ai_suggestions.weaknesses:
        counts[w.priority] = counts.get(w.priority, 0) + 1

    cols = st.columns(4)
    cols[0].metric("High Priority Issues", counts["High Priority"])
    cols[1].metric("Medium Priority Issues", counts["Medium Priority"])
    cols[2].metric("Low Priority Issues", counts["Low Priority"])
    cols[3].metric("Bullets Improved", len(ai_suggestions.experience))


def _build_summary_dict(
    ats_report: ATSReport | None,
    skill_result: SkillExtractionResult | None,
    match_report: MatchReport | None,
    learning_plan: LearningPlan | None,
    ai_suggestions: AIResumeSuggestions | None,
) -> dict:
    """Bundle already-computed numbers for the download button. No new computation."""
    return {
        "ats_score": ats_report.overall_score if ats_report else None,
        "skills_detected": skill_result.all_detected if skill_result else [],
        "job_match_percent": match_report.overall_match_percent if match_report else None,
        "skill_gap_total_missing": learning_plan.total_missing if learning_plan else None,
        "ai_suggestions_weakness_count": len(ai_suggestions.weaknesses) if ai_suggestions else None,
    }


def render_dashboard(
    parsed: ParsedResume | None,
    ats_report: ATSReport | None,
    skill_result: SkillExtractionResult | None,
    match_report: MatchReport | None,
    learning_plan: LearningPlan | None,
    ai_suggestions: AIResumeSuggestions | None,
) -> None:
    """
    Full Dashboard page layout. Every argument is read-only data the
    caller already has — this function computes nothing new.
    """
    if parsed is None:
        st.info("Upload a resume on the **Resume Upload** page first.", icon="📤")
        return

    st.subheader("Resume Analysis Pipeline")
    render_pipeline_overview(parsed, ats_report, skill_result, match_report, learning_plan, ai_suggestions)
    st.divider()

    metric_cols = st.columns(3)
    metric_cols[0].metric("ATS Score", f"{ats_report.overall_score:.1f}/100" if ats_report else "N/A")
    metric_cols[1].metric("Skills Detected", len(skill_result.all_detected) if skill_result else 0)
    metric_cols[2].metric(
        "Job Match", f"{match_report.overall_match_percent:.1f}%" if match_report else "N/A"
    )
    st.divider()

    if ats_report is not None or skill_result is not None:
        row1 = st.columns(2)
        with row1[0]:
            if ats_report is not None:
                st.plotly_chart(ats_score_gauge(ats_report), use_container_width=True)
        with row1[1]:
            if skill_result is not None:
                st.plotly_chart(skill_distribution_pie(skill_result), use_container_width=True)

    if ats_report is not None:
        row2 = st.columns(2)
        with row2[0]:
            st.plotly_chart(resume_strength_radar(ats_report), use_container_width=True)
        with row2[1]:
            st.plotly_chart(ats_weak_sections_bar(ats_report), use_container_width=True)

    st.subheader("Job Match")
    if match_report is not None:
        row3 = st.columns(2)
        with row3[0]:
            st.plotly_chart(job_match_gauge(match_report), use_container_width=True)
        with row3[1]:
            st.plotly_chart(job_match_signals_bar(match_report), use_container_width=True)
    else:
        st.info(
            "Run **Job Matching** to see match visualizations here — the "
            "dashboard reads existing results only, it never runs a new match.",
            icon="🎯",
        )

    if learning_plan is not None and learning_plan.total_missing > 0:
        st.subheader("Skill Gap")
        st.plotly_chart(skill_gap_priority_bar(learning_plan), use_container_width=True)

    st.divider()
    render_ai_suggestions_summary(ai_suggestions)

    st.divider()
    summary = _build_summary_dict(ats_report, skill_result, match_report, learning_plan, ai_suggestions)
    st.download_button(
        "Download dashboard summary (JSON)",
        data=json.dumps(summary, indent=2, default=str),
        file_name="dashboard_summary.json",
        mime="application/json",
    )
