"""
matching/cosine_similarity.py
---------------------------------
TF-IDF-based cosine similarity between a resume and a job description.

This is deliberately separate from semantic_match.py's embedding-based
similarity: TF-IDF cosine similarity is fast, needs no model download,
and rewards exact term overlap — a useful, literal complement to
semantic similarity's "meaning" based score. It also serves as the
graceful-degradation path if the sentence-transformers model can't be
loaded (e.g. no internet on first run).
"""

from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as _sk_cosine_similarity

from utils.logger import get_logger

logger = get_logger(__name__)


def compute_cosine_similarity(resume_text: str, jd_text: str) -> float:
    """
    Compute TF-IDF cosine similarity between two texts, returned as 0-100.

    Returns 0.0 if either text is empty or too sparse to vectorize
    (e.g. only stopwords) rather than raising.
    """
    if not resume_text.strip() or not jd_text.strip():
        return 0.0

    try:
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vectorizer.fit_transform([resume_text, jd_text])
        similarity = _sk_cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return round(float(similarity) * 100, 1)
    except ValueError as exc:
        # e.g. "empty vocabulary; perhaps the documents only contain stop words"
        logger.warning("Cosine similarity could not be computed: {}", exc)
        return 0.0
