"""
utils/helper.py
-----------------
Small, generic helper functions used across multiple modules.
Nothing domain-specific belongs here — resume/ATS/matching logic
lives in its own package (parser/, ats/, matching/, etc.).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    """Load and return JSON content from a file path."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Any, path: Path) -> None:
    """Save `data` as pretty-printed JSON to `path`, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def truncate(text: str, max_length: int = 120) -> str:
    """Truncate `text` to `max_length` chars, appending an ellipsis if cut."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "\u2026"


def percentage(part: float, whole: float) -> float:
    """Safe percentage calculation; returns 0.0 if `whole` is 0."""
    if whole == 0:
        return 0.0
    return round((part / whole) * 100, 2)
