import math
from collections.abc import Sequence
from dataclasses import replace

from findr.domain.models import SearchResult
from findr.domain.ports import UsageRepository


class UsageAwareRanking:
    """Sorts by relevance, boosting results the user opens often (frecency-lite)."""

    MAX_BOOST = 0.2
    SATURATION_COUNT = 20

    def __init__(self, usage: UsageRepository) -> None:
        self._usage = usage

    def rank(self, results: Sequence[SearchResult]) -> list[SearchResult]:
        boosted = [replace(result, score=result.score + self._boost(result.id)) for result in results]
        return sorted(boosted, key=lambda result: result.score, reverse=True)

    def _boost(self, result_id: str) -> float:
        count = self._usage.usage_count(result_id)
        if count <= 0:
            return 0.0
        return self.MAX_BOOST * min(1.0, math.log1p(count) / math.log1p(self.SATURATION_COUNT))
