"""
matching/semantic_match.py
------------------------------
Semantic similarity between a resume and a job description using
sentence-transformer embeddings (config.settings.semantic_model_name,
default "all-MiniLM-L6-v2").

Unlike TF-IDF cosine similarity, this captures meaning rather than
exact wording — "built REST APIs" and "developed backend web services"
score as similar even though they share almost no exact tokens.

The model is downloaded from Hugging Face on first use and cached
locally after that, so the very first call needs internet access; every
call after that works offline. If the model can't be loaded (no
internet and no local cache yet), this degrades gracefully by returning
(None, [warning]) rather than crashing the matching pipeline — the
caller falls back to TF-IDF cosine similarity instead.
"""

from __future__ import annotations

from utils.logger import get_logger

logger = get_logger(__name__)

_MODEL = None
_MODEL_LOAD_ATTEMPTED = False


def _get_model():
    """Lazily load and cache the sentence-transformer model."""
    global _MODEL, _MODEL_LOAD_ATTEMPTED
    if _MODEL is not None or _MODEL_LOAD_ATTEMPTED:
        return _MODEL

    _MODEL_LOAD_ATTEMPTED = True
    try:
        from sentence_transformers import SentenceTransformer

        from config import settings

        _MODEL = SentenceTransformer(settings.semantic_model_name)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Could not load sentence-transformers model ({}); semantic "
            "similarity will be unavailable for this session.",
            exc,
        )
        _MODEL = None
    return _MODEL


def compute_semantic_similarity(
    resume_text: str, jd_text: str
) -> tuple[float | None, list[str]]:
    """
    Compute embedding-based semantic similarity between two texts, as 0-100.

    Returns (score, warnings). `score` is None if the model couldn't be
    loaded — callers should fall back to TF-IDF cosine similarity in
    that case rather than treating None as a 0 score.
    """
    warnings: list[str] = []

    if not resume_text.strip() or not jd_text.strip():
        return 0.0, warnings

    model = _get_model()
    if model is None:
        warnings.append(
            "Semantic similarity model unavailable (likely no internet "
            "access to download it on first use) — falling back to "
            "keyword/TF-IDF based matching only."
        )
        return None, warnings

    try:
        import numpy as np

        embeddings = model.encode([resume_text, jd_text])
        a, b = embeddings[0], embeddings[1]
        denom = (np.linalg.norm(a) * np.linalg.norm(b))
        similarity = float(np.dot(a, b) / denom) if denom else 0.0
        similarity = max(0.0, min(1.0, similarity))  # clamp for float drift
        return round(similarity * 100, 1), warnings
    except Exception as exc:  # noqa: BLE001
        logger.warning("Semantic similarity computation failed: {}", exc)
        warnings.append("Semantic similarity computation failed; falling back to TF-IDF matching only.")
        return None, warnings
