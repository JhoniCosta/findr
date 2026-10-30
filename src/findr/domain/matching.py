"""Fuzzy relevance scoring used by every text-based provider."""

from collections.abc import Iterable

from findr.domain.query import Query
from findr.domain.text import normalize, split_words


class FuzzyMatcher:
    """Scores how well a query matches a text, in [0, 1] (0 means "no match").

    Tiers, best first: exact, prefix, word prefix, acronym, substring, subsequence.
    Within a tier, matches that cover more of the candidate rank higher.
    """

    EXACT = 1.0
    PREFIX = 0.9
    WORD_PREFIX = 0.8
    ACRONYM = 0.75
    SUBSTRING = 0.65
    SUBSEQUENCE_MAX = 0.5
    TIER_SPREAD = 0.09
    MULTI_TOKEN_PENALTY = 0.9
    MIN_SUBSEQUENCE_LENGTH = 3
    MIN_SUBSEQUENCE_QUALITY = 0.35

    def score(self, query: Query, text: str) -> float:
        candidate = normalize(text)
        if query.is_empty or not candidate:
            return 0.0

        whole = self._score_term(query.normalized, candidate)
        if whole or len(query.tokens) == 1:
            return whole

        token_scores = [self._score_term(token, candidate) for token in query.tokens]
        if not all(token_scores):
            return 0.0
        return self.MULTI_TOKEN_PENALTY * sum(token_scores) / len(token_scores)

    def best_score(self, query: Query, weighted_fields: Iterable[tuple[str | None, float]]) -> float:
        """Best ``score * weight`` among several fields of the same item (name, keywords, ...)."""
        return max(
            (self.score(query, text) * weight for text, weight in weighted_fields if text),
            default=0.0,
        )

    def _score_term(self, term: str, candidate: str) -> float:
        if candidate == term:
            return self.EXACT

        coverage = len(term) / len(candidate)
        if candidate.startswith(term):
            return self.PREFIX + self.TIER_SPREAD * coverage

        words = split_words(candidate)
        if any(word.startswith(term) for word in words):
            return self.WORD_PREFIX + self.TIER_SPREAD * coverage

        if len(term) >= 2 and "".join(word[0] for word in words).startswith(term):
            return self.ACRONYM

        if term in candidate:
            return self.SUBSTRING + self.TIER_SPREAD * coverage

        return self.SUBSEQUENCE_MAX * self._subsequence_quality(term, candidate)

    def _subsequence_quality(self, term: str, candidate: str) -> float:
        """How tightly the characters of ``term`` appear, in order, inside ``candidate``."""
        if len(term) < self.MIN_SUBSEQUENCE_LENGTH:
            return 0.0

        positions: list[int] = []
        start = 0
        for char in term:
            index = candidate.find(char, start)
            if index < 0:
                return 0.0
            positions.append(index)
            start = index + 1

        span = positions[-1] - positions[0] + 1
        quality = len(term) / span
        return quality if quality >= self.MIN_SUBSEQUENCE_QUALITY else 0.0
