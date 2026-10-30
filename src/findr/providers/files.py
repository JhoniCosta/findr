import heapq
import mimetypes
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from findr.domain.actions import OpenPath, RevealPath
from findr.domain.icons import icon_for_mime_type, themed_icon
from findr.domain.matching import FuzzyMatcher
from findr.domain.models import ResultKind, SearchResult
from findr.domain.ports import SearchProvider
from findr.domain.query import Query


@dataclass(frozen=True, slots=True)
class IndexedFile:
    path: str
    name: str
    normalized_name: str
    is_dir: bool
    depth: int


class FileIndex(Protocol):
    def candidates(self, tokens: tuple[str, ...]) -> Iterator[IndexedFile]:
        """Entries whose normalized name contains every token (cheap pre-filter)."""
        ...


class FileProvider(SearchProvider):
    """Searches file and folder names in the background-built index."""

    name = "files"

    FOLDER_WEIGHT = 0.85
    FILE_WEIGHT = 0.8
    DEPTH_PENALTY = 0.02
    MIN_QUERY_LENGTH = 2

    def __init__(self, index: FileIndex, matcher: FuzzyMatcher, max_results: int, home: Path | None = None) -> None:
        self._index = index
        self._matcher = matcher
        self._max_results = max_results
        self._home = str(home or Path.home())

    def search(self, query: Query) -> Iterable[SearchResult]:
        if len(query.normalized) < self.MIN_QUERY_LENGTH:
            return []
        scored = ((self._score(query, entry), entry) for entry in self._index.candidates(query.tokens))
        best = heapq.nlargest(self._max_results, scored, key=lambda pair: pair[0])
        return [self._to_result(entry, score) for score, entry in best if score > 0]

    def _score(self, query: Query, entry: IndexedFile) -> float:
        weight = self.FOLDER_WEIGHT if entry.is_dir else self.FILE_WEIGHT
        depth_factor = max(0.5, 1 - self.DEPTH_PENALTY * entry.depth)
        return self._matcher.score(query, entry.name) * weight * depth_factor

    def _to_result(self, entry: IndexedFile, score: float) -> SearchResult:
        return SearchResult(
            id=f"path:{entry.path}",
            title=entry.name,
            subtitle=self._display_parent(entry.path),
            kind=ResultKind.FOLDER if entry.is_dir else ResultKind.FILE,
            score=score,
            action=OpenPath(entry.path),
            alternate_action=RevealPath(entry.path),
            icon=self._icon(entry),
        )

    def _display_parent(self, path: str) -> str:
        parent = str(Path(path).parent)
        if parent == self._home or parent.startswith(self._home + "/"):
            return "~" + parent[len(self._home):]
        return parent

    @staticmethod
    def _icon(entry: IndexedFile) -> str:
        if entry.is_dir:
            return themed_icon("folder")
        mime_type, _ = mimetypes.guess_type(entry.name, strict=False)
        return icon_for_mime_type(mime_type)
