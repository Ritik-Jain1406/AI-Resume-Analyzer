"""
matching/keyword_match.py
-----------------------------
Keyword-coverage matching: extracts the most frequent, meaningful terms
from a job description and checks how many appear in the resume.

Deliberately uses scikit-learn's built-in English stopword list rather
than NLTK's, so this module works fully offline with no corpus download
required — keeping keyword/cosine matching usable even in environments
where the semantic model (Phase 5's other similarity signal) can't be
downloaded.
"""

from __future__ import annotations

import re
from collections import Counter

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

# Matches words made of letters plus a few characters common in tech
# terms (C++, Node.js, CI/CD, C#) so those survive tokenization intact.
_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.#-]{2,}")

DEFAULT_TOP_N_KEYWORDS = 30


def _tokenize(text: str) -> list[str]:
    tokens = [t.lower().rstrip(".") for t in _TOKEN_RE.findall(text)]
    return [t for t in tokens if t]


def extract_keywords(text: str, top_n: int = DEFAULT_TOP_N_KEYWORDS) -> list[str]:
    """Return the `top_n` most frequent non-stopword tokens in `text`, most frequent first."""
    tokens = [t for t in _tokenize(text) if t not in ENGLISH_STOP_WORDS]
    counts = Counter(tokens)
    return [token for token, _ in counts.most_common(top_n)]


def compute_keyword_coverage(
    resume_text: str, jd_text: str, top_n: int = DEFAULT_TOP_N_KEYWORDS
) -> tuple[float, list[str], list[str]]:
    """
    Score what fraction of the JD's top keywords appear anywhere in the resume.

    Returns (coverage_percent, matched_keywords, missing_keywords).
    """
    jd_keywords = extract_keywords(jd_text, top_n=top_n)
    if not jd_keywords:
        return 0.0, [], []

    resume_tokens = set(_tokenize(resume_text))
    matched = [k for k in jd_keywords if k in resume_tokens]
    missing = [k for k in jd_keywords if k not in resume_tokens]

    coverage = round((len(matched) / len(jd_keywords)) * 100, 1)
    return coverage, matched, missing
