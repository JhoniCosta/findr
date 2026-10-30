"""Abstractions the services depend on (ports in a ports-and-adapters architecture)."""

from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from typing import Protocol

from findr.domain.models import SearchResult
from findr.domain.query import Query


class SearchProvider(ABC):
    """Strategy for one source of results (apps, files, calculator, ...).

    ``search`` runs on a worker thread, so implementations must only read
    thread-safe snapshots of their data.
    """

    name: str

    @abstractmethod
    def search(self, query: Query) -> Iterable[SearchResult]: ...


class UsageRepository(Protocol):
    """Remembers which results the user opens, so they can be ranked higher next time."""

    def usage_count(self, result_id: str) -> int: ...

    def record_usage(self, result_id: str) -> None: ...


class RankingPolicy(Protocol):
    def rank(self, results: Sequence[SearchResult]) -> list[SearchResult]: ...
