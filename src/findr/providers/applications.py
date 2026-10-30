from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol

from findr.domain.actions import LaunchApplication
from findr.domain.matching import FuzzyMatcher
from findr.domain.models import ResultKind, SearchResult
from findr.domain.ports import SearchProvider
from findr.domain.query import Query


@dataclass(frozen=True, slots=True)
class AppEntry:
    app_id: str
    name: str
    description: str = ""
    generic_name: str = ""
    keywords: tuple[str, ...] = ()
    executable: str = ""
    icon: str | None = None


class AppCatalog(Protocol):
    """Read-only, thread-safe snapshot of the installed applications."""

    def entries(self) -> Sequence[AppEntry]: ...


class ApplicationProvider(SearchProvider):
    name = "applications"

    NAME_WEIGHT = 1.0
    KEYWORD_WEIGHT = 0.85
    GENERIC_NAME_WEIGHT = 0.8
    EXECUTABLE_WEIGHT = 0.75
    DESCRIPTION_WEIGHT = 0.5

    def __init__(self, catalog: AppCatalog, matcher: FuzzyMatcher) -> None:
        self._catalog = catalog
        self._matcher = matcher

    def search(self, query: Query) -> Iterable[SearchResult]:
        for app in self._catalog.entries():
            score = self._matcher.best_score(query, self._weighted_fields(app))
            if score > 0:
                yield SearchResult(
                    id=f"app:{app.app_id}",
                    title=app.name,
                    subtitle=app.description or app.generic_name or "Aplicativo",
                    kind=ResultKind.APPLICATION,
                    score=score,
                    action=LaunchApplication(app.app_id),
                    icon=app.icon,
                )

    def _weighted_fields(self, app: AppEntry) -> Iterable[tuple[str | None, float]]:
        yield app.name, self.NAME_WEIGHT
        yield app.generic_name, self.GENERIC_NAME_WEIGHT
        yield app.executable, self.EXECUTABLE_WEIGHT
        yield app.description, self.DESCRIPTION_WEIGHT
        for keyword in app.keywords:
            yield keyword, self.KEYWORD_WEIGHT
