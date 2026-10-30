from collections.abc import Sequence

from findr.domain.models import ResultGroup, ResultKind, SearchResult


class ResultGrouper:
    """Spotlight-style layout: a "top hit" first, then one section per kind.

    Sections are ordered by their best result, which ``ranked`` already reflects.
    """

    def __init__(self, max_per_kind: int) -> None:
        if max_per_kind < 1:
            raise ValueError("max_per_kind must be positive")
        self._max_per_kind = max_per_kind

    def group(self, ranked: Sequence[SearchResult]) -> list[ResultGroup]:
        if not ranked:
            return []

        groups: list[ResultGroup] = []
        remaining = list(ranked)
        if remaining[0].kind is not ResultKind.WEB:
            groups.append(ResultGroup(kind=None, results=(remaining.pop(0),)))

        by_kind: dict[ResultKind, list[SearchResult]] = {}
        for result in remaining:
            bucket = by_kind.setdefault(result.kind, [])
            if len(bucket) < self._max_per_kind:
                bucket.append(result)

        groups.extend(ResultGroup(kind=kind, results=tuple(items)) for kind, items in by_kind.items())
        return groups
