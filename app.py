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

import tempfile
from pathlib import Path

import streamlit as st

from config import settings, ensure_directories
from parser.resume_parser import parse_resume
from parser.schemas import ParsedResume
from utils.logger import get_logger
from utils.validators import ValidationError, validate_file_size

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

    st.subheader("Structured Output (JSON)")
    st.json(parsed.model_dump())

    st.download_button(
        "Download parsed JSON",
        data=parsed.model_dump_json(indent=2),
        file_name=f"{Path(parsed.source_filename).stem}_parsed.json",
        mime="application/json",
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
    else:
        render_placeholder(selected_page)


if __name__ == "__main__":
    main()
