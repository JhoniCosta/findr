import logging
from collections.abc import Iterable, Sequence

from findr.domain.models import ResultGroup, SearchResult
from findr.domain.ports import RankingPolicy, SearchProvider
from findr.domain.query import Query
from findr.services.grouping import ResultGrouper

logger = logging.getLogger(__name__)


class SearchEngine:
    """Facade over the providers: fan out the query, merge, rank and group.

    A failing provider is logged and skipped, so one broken source never
    breaks the whole search bar.
    """

    def __init__(self, providers: Sequence[SearchProvider], ranking: RankingPolicy, grouper: ResultGrouper) -> None:
        self._providers = tuple(providers)
        self._ranking = ranking
        self._grouper = grouper

    def search(self, raw_query: str) -> list[ResultGroup]:
        query = Query.parse(raw_query)
        if query.is_empty:
            return []
        ranked = self._ranking.rank(self._deduplicate(self._collect(query)))
        return self._grouper.group(ranked)

    def _collect(self, query: Query) -> Iterable[SearchResult]:
        for provider in self._providers:
            try:
                yield from provider.search(query)
            except Exception:
                logger.exception("search provider %r failed", provider.name)

    @staticmethod
    def _deduplicate(results: Iterable[SearchResult]) -> list[SearchResult]:
        best: dict[str, SearchResult] = {}
        for result in results:
            current = best.get(result.id)
            if current is None or result.score > current.score:
                best[result.id] = result
        return list(best.values())
