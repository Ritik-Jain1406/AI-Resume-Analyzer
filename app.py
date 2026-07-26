"""
app.py
------
Streamlit entry point for the AI Resume Analyzer.

Phase 1 scope: this wires up the app shell, sidebar navigation, config,
and logging — enough to prove the project structure works end to end.
Each "page" is a placeholder that later phases will fill in with real
functionality (parsing, ATS scoring, matching, etc.).
"""

from __future__ import annotations

import streamlit as st

from config import settings, ensure_directories
from utils.logger import get_logger

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
    else:
        render_placeholder(selected_page)


if __name__ == "__main__":
    main()
