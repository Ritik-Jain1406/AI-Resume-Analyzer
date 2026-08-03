"""
visualization/charts.py
--------------------------
Phase 8: pure presentation functions. Every function here takes an
*already-computed* Phase 3/4/5/6/7 pydantic object as input and returns
a plotly.graph_objects.Figure — nothing in this file computes a score,
calls an API, or derives a number that doesn't already exist on the
input model. If a chart needs data that isn't already on the model,
that's a signal the chart shouldn't exist yet, not something to compute
here.
"""

from __future__ import annotations

import plotly.graph_objects as go

from ats.schemas import ATSReport
from matching.schemas import LearningPlan, MatchReport
from parser.schemas import SkillExtractionResult

# Color bands reused across charts for a consistent "red/yellow/green" reading
_SCORE_COLORS = {"low": "#e74c3c", "mid": "#f1c40f", "high": "#2ecc71"}


def _score_color(score: float) -> str:
    if score >= 75:
        return _SCORE_COLORS["high"]
    if score >= 50:
        return _SCORE_COLORS["mid"]
    return _SCORE_COLORS["low"]


def ats_score_gauge(ats_report: ATSReport) -> go.Figure:
    """Donut-style gauge for the overall ATS score (0-100)."""
    score = ats_report.overall_score
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "/100"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": _score_color(score)},
                "steps": [
                    {"range": [0, 50], "color": "#fdecea"},
                    {"range": [50, 75], "color": "#fef9e7"},
                    {"range": [75, 100], "color": "#eafaf1"},
                ],
            },
            title={"text": "ATS Score"},
        )
    )
    fig.update_layout(height=280, margin=dict(l=20, r=20, t=50, b=20))
    return fig


def ats_weak_sections_bar(ats_report: ATSReport) -> go.Figure:
    """Horizontal bar chart of every ATS check, sorted weakest-first."""
    checks = sorted(ats_report.checks, key=lambda c: c.score)
    names = [c.name for c in checks]
    scores = [c.score for c in checks]
    colors = [_score_color(s) for s in scores]

    fig = go.Figure(
        go.Bar(
            x=scores,
            y=names,
            orientation="h",
            marker_color=colors,
            text=[f"{s:.0f}" for s in scores],
            textposition="outside",
        )
    )
    fig.update_layout(
        title="Weak Sections (lowest scoring first)",
        xaxis=dict(title="Score", range=[0, 105]),
        height=max(250, 45 * len(checks)),
        margin=dict(l=10, r=30, t=50, b=30),
    )
    return fig


def resume_strength_radar(ats_report: ATSReport) -> go.Figure:
    """Radar chart giving a holistic shape across all ATS check categories."""
    checks = ats_report.checks
    categories = [c.name for c in checks]
    scores = [c.score for c in checks]
    # close the loop so the radar polygon connects back to the first point
    categories_closed = categories + [categories[0]] if categories else []
    scores_closed = scores + [scores[0]] if scores else []

    fig = go.Figure(
        go.Scatterpolar(
            r=scores_closed,
            theta=categories_closed,
            fill="toself",
            line_color="#3498db",
        )
    )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        title="Resume Strength",
        height=350,
        margin=dict(l=40, r=40, t=50, b=30),
    )
    return fig


def skill_distribution_pie(skill_result: SkillExtractionResult) -> go.Figure:
    """Pie chart of detected skills grouped by category."""
    labels = [cat for cat, skills in skill_result.detected_by_category.items() if skills]
    values = [len(skills) for skills in skill_result.detected_by_category.values() if skills]

    if not labels:
        # Degenerate state: no skills detected at all. A single explanatory
        # slice reads more clearly in a pie chart than an empty canvas.
        fig = go.Figure(go.Pie(labels=["No skills detected"], values=[1], marker_colors=["#dcdcdc"]))
    else:
        fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.35))

    fig.update_layout(title="Skill Distribution by Category", height=350, margin=dict(l=20, r=20, t=50, b=20))
    return fig


def job_match_gauge(match_report: MatchReport) -> go.Figure:
    """Donut-style gauge for the overall job match percentage."""
    score = match_report.overall_match_percent
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "%"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": _score_color(score)},
                "steps": [
                    {"range": [0, 50], "color": "#fdecea"},
                    {"range": [50, 75], "color": "#fef9e7"},
                    {"range": [75, 100], "color": "#eafaf1"},
                ],
            },
            title={"text": "Job Match"},
        )
    )
    fig.update_layout(height=280, margin=dict(l=20, r=20, t=50, b=20))
    return fig


def job_match_signals_bar(match_report: MatchReport) -> go.Figure:
    """Grouped bar chart comparing the four match signals side by side."""
    signals = ["Semantic", "Cosine", "Keyword", "Skill"]
    values = [
        match_report.semantic_similarity if match_report.semantic_available else 0,
        match_report.cosine_similarity,
        match_report.keyword_coverage,
        match_report.skill_match_percent,
    ]
    colors = [_score_color(v) for v in values]

    fig = go.Figure(go.Bar(x=signals, y=values, marker_color=colors, text=[f"{v:.0f}" for v in values], textposition="outside"))
    fig.update_layout(
        title="Match Signal Breakdown",
        yaxis=dict(title="Score (%)", range=[0, 105]),
        height=300,
        margin=dict(l=30, r=20, t=50, b=30),
    )
    return fig


def skill_gap_priority_bar(learning_plan: LearningPlan) -> go.Figure:
    """Bar chart of missing-skill counts by priority tier."""
    tiers = ["High Priority", "Medium Priority", "Low Priority"]
    counts = [
        learning_plan.high_priority_count,
        learning_plan.medium_priority_count,
        learning_plan.low_priority_count,
    ]
    colors = [_SCORE_COLORS["low"], _SCORE_COLORS["mid"], _SCORE_COLORS["high"]]

    fig = go.Figure(go.Bar(x=tiers, y=counts, marker_color=colors, text=counts, textposition="outside"))
    fig.update_layout(
        title="Skill Gap by Priority",
        yaxis=dict(title="Missing skills", rangemode="tozero"),
        height=300,
        margin=dict(l=30, r=20, t=50, b=30),
    )
    return fig
