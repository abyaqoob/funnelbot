"""FAQ matching engine using TF-IDF and Cosine Similarity."""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models.faq import FAQConfidence, FAQItem, FAQMatchResult


class FAQMatcher:
    """Matches user queries against knowledge base FAQs using TF-IDF and Cosine Similarity."""

    HIGH_THRESHOLD: float = 0.55
    MEDIUM_THRESHOLD: float = 0.30

    def __init__(self, faqs: list[FAQItem] | None = None):
        self.vectorizer: TfidfVectorizer | None = None
        self.matrix: np.ndarray | None = None
        self.corpus_entries: list[tuple[str, FAQItem]] = []
        if faqs:
            self.fit(faqs)

    def fit(self, faqs: list[FAQItem]) -> None:
        """Fit vectorizer on all active FAQ questions and variants."""
        self.corpus_entries = []
        corpus_texts: list[str] = []

        for faq in faqs:
            if not faq.is_active:
                continue
            for q in faq.all_questions():
                q_clean = q.strip()
                if q_clean:
                    self.corpus_entries.append((q_clean, faq))
                    corpus_texts.append(q_clean)

        if not corpus_texts:
            self.vectorizer = None
            self.matrix = None
            return

        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words="english",
            lowercase=True,
        )
        self.matrix = self.vectorizer.fit_transform(corpus_texts)

    def match(self, query: str) -> FAQMatchResult:
        """
        Compute similarity of query against FAQ knowledge base.
        Returns FAQMatchResult with confidence level:
          - HIGH (>= 0.55): Auto-answer
          - MEDIUM (0.30 - 0.55): "Did you mean: <closest>?"
          - LOW (< 0.30): Fallback message + human flag
        """
        clean_query = query.strip()
        if not clean_query or not self.vectorizer or self.matrix is None or not self.corpus_entries:
            return FAQMatchResult(
                faq=None,
                matched_query=None,
                score=0.0,
                confidence=FAQConfidence.LOW,
            )

        clean_lower = clean_query.lower().strip("?!. ")

        # 1. Exact match check (handles short phrases perfectly)
        for question_text, faq_item in self.corpus_entries:
            if clean_lower == question_text.lower().strip("?!. "):
                return FAQMatchResult(
                    faq=faq_item,
                    matched_query=question_text,
                    score=1.0,
                    confidence=FAQConfidence.HIGH,
                )

        # 2. TF-IDF Cosine Similarity
        best_score = 0.0
        best_idx = 0

        try:
            query_vec = self.vectorizer.transform([clean_query])
            similarities = cosine_similarity(query_vec, self.matrix)[0]
            if len(similarities) > 0:
                best_idx = int(np.argmax(similarities))
                best_score = float(similarities[best_idx])
        except Exception:
            best_score = 0.0

        if not self.corpus_entries:
            return FAQMatchResult(faq=None, matched_query=None, score=0.0, confidence=FAQConfidence.LOW)

        matched_question, best_faq = self.corpus_entries[best_idx]

        # Determine confidence tier
        if best_score >= self.HIGH_THRESHOLD:
            confidence = FAQConfidence.HIGH
        elif best_score >= self.MEDIUM_THRESHOLD:
            confidence = FAQConfidence.MEDIUM
        else:
            confidence = FAQConfidence.LOW

        return FAQMatchResult(
            faq=best_faq if best_score >= self.MEDIUM_THRESHOLD else None,
            matched_query=matched_question if best_score >= self.MEDIUM_THRESHOLD else None,
            score=round(best_score, 4),
            confidence=confidence,
        )
