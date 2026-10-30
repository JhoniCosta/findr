"""Test doubles shared by the test modules."""

from collections.abc import Iterable

from findr.domain.models import ResultKind, SearchResult
from findr.domain.actions import OpenUri
from findr.domain.ports import SearchProvider
from findr.domain.query import Query


def make_result(result_id: str, score: float, kind: ResultKind = ResultKind.APPLICATION) -> SearchResult:
    return SearchResult(id=result_id, title=result_id, subtitle="", kind=kind, score=score,
                        action=OpenUri(f"file:///{result_id}"))


class StaticProvider(SearchProvider):
    def __init__(self, results: Iterable[SearchResult], name: str = "static") -> None:
        self.name = name
        self._results = list(results)

    def search(self, query: Query) -> Iterable[SearchResult]:
        return list(self._results)


class FailingProvider(SearchProvider):
    name = "failing"

    def search(self, query: Query) -> Iterable[SearchResult]:
        raise RuntimeError("boom")


class InMemoryUsage:
    def __init__(self, counts: dict[str, int] | None = None) -> None:
        self.counts = dict(counts or {})

    def usage_count(self, result_id: str) -> int:
        return self.counts.get(result_id, 0)

    def record_usage(self, result_id: str) -> None:
        self.counts[result_id] = self.counts.get(result_id, 0) + 1


class RecordingDesktop:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def launch_application(self, app_id: str) -> None:
        self.calls.append(("launch", app_id))

    def open_uri(self, uri: str) -> None:
        self.calls.append(("open", uri))

    def reveal_path(self, path: str) -> None:
        self.calls.append(("reveal", path))

    def copy_text(self, text: str) -> None:
        self.calls.append(("copy", text))
