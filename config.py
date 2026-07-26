"""
config.py
---------
Central configuration for the AI Resume Analyzer.

All paths, constants, and tunable parameters used across the project
should be read from here rather than hard-coded in individual modules.
This keeps the app configurable via environment variables (.env) while
still giving safe, sensible defaults for local development.
"""

from __future__ import annotations

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# --------------------------------------------------------------------------- #
# Base paths
# --------------------------------------------------------------------------- #
BASE_DIR: Path = Path(__file__).resolve().parent
DATA_DIR: Path = BASE_DIR / "data"
ASSETS_DIR: Path = BASE_DIR / "assets"
RESUME_SAMPLES_DIR: Path = DATA_DIR / "resume_samples"
JOB_DESCRIPTIONS_DIR: Path = DATA_DIR / "job_descriptions"
LOGS_DIR: Path = BASE_DIR / "logs"
DB_DIR: Path = BASE_DIR / "database"


class Settings(BaseSettings):
    """
    Application-wide settings.

    Values can be overridden via a `.env` file or real environment
    variables (e.g. APP_ENV=production, LOG_LEVEL=DEBUG).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App metadata ---
    app_name: str = "AI Resume Analyzer"
    app_env: str = Field(default="development")  # development | production
    debug: bool = Field(default=True)

    # --- Logging ---
    log_level: str = Field(default="INFO")
    log_file: Path = LOGS_DIR / "app.log"
    log_rotation: str = "5 MB"
    log_retention: str = "10 days"

    # --- Database ---
    database_url: str = Field(default=f"sqlite:///{DB_DIR / 'resume_analyzer.db'}")

    # --- Resume parsing ---
    allowed_resume_extensions: tuple[str, ...] = (".pdf", ".docx")
    max_resume_size_mb: int = 5

    # --- ATS scoring ---
    ats_pass_threshold: int = 70  # percentage

    # --- Matching ---
    semantic_model_name: str = "all-MiniLM-L6-v2"
    match_pass_threshold: int = 60  # percentage

    # --- Skills data ---
    skills_csv: Path = DATA_DIR / "skills.csv"
    job_roles_csv: Path = DATA_DIR / "job_roles.csv"


settings = Settings()


def ensure_directories() -> None:
    """Create any runtime directories the app expects to exist."""
    for directory in (DATA_DIR, ASSETS_DIR, RESUME_SAMPLES_DIR,
                      JOB_DESCRIPTIONS_DIR, LOGS_DIR, DB_DIR):
        directory.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    ensure_directories()
    print(settings.model_dump())
