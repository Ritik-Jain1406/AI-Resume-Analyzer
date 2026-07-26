"""
utils/logger.py
----------------
Centralized logging setup using loguru.

Import `get_logger` anywhere in the project instead of configuring
logging per-module:

    from utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Resume parsed successfully")
"""

from __future__ import annotations

import sys
from loguru import logger as _logger

from config import settings, LOGS_DIR

_CONFIGURED = False


def _configure() -> None:
    """Configure loguru sinks exactly once per process."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    _logger.remove()  # drop the default stderr handler so we control format

    # Console sink — human-readable, colorized
    _logger.add(
        sys.stderr,
        level=settings.log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )

    # File sink — rotated, retained, useful for debugging deployed runs
    _logger.add(
        settings.log_file,
        level=settings.log_level,
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        enqueue=True,
        backtrace=True,
        diagnose=False,  # keep tracebacks free of local variable values (resume PII)
    )

    _CONFIGURED = True


def get_logger(name: str):
    """Return a loguru logger bound with the calling module's name."""
    _configure()
    return _logger.bind(module=name)
