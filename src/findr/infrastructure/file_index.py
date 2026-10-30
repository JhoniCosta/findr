import logging
import os
import threading
from collections import deque
from collections.abc import Iterable, Iterator

from findr.domain.text import normalize
from findr.providers.files import IndexedFile

logger = logging.getLogger(__name__)


class FileSystemIndex:
    """In-memory index of file and folder names, rebuilt periodically on a daemon thread.

    The crawl is breadth-first, so when ``max_entries`` is reached the shallow
    (usually more relevant) entries are the ones kept. Readers always see a
    complete snapshot: the list is built aside and swapped in one assignment.
    """

    def __init__(
        self,
        roots: Iterable[str],
        excluded_names: Iterable[str],
        max_depth: int,
        max_entries: int,
        include_hidden: bool = False,
    ) -> None:
        self._roots = tuple(roots)
        self._excluded = frozenset(excluded_names)
        self._max_depth = max_depth
        self._max_entries = max_entries
        self._include_hidden = include_hidden
        self._entries: tuple[IndexedFile, ...] = ()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __len__(self) -> int:
        return len(self._entries)

    def candidates(self, tokens: tuple[str, ...]) -> Iterator[IndexedFile]:
        snapshot = self._entries
        for entry in snapshot:
            if all(token in entry.normalized_name for token in tokens):
                yield entry

    def rebuild(self) -> None:
        entries = list(self._crawl())
        self._entries = tuple(entries)
        logger.info("file index rebuilt: %d entries", len(entries))

    def start_background_refresh(self, interval_seconds: float) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._refresh_loop, args=(interval_seconds,), name="findr-file-index", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _refresh_loop(self, interval_seconds: float) -> None:
        while not self._stop.is_set():
            try:
                self.rebuild()
            except Exception:
                logger.exception("file index rebuild failed")
            self._stop.wait(interval_seconds)

    def _crawl(self) -> Iterator[IndexedFile]:
        pending: deque[tuple[str, int]] = deque((root, 0) for root in self._roots if os.path.isdir(root))
        produced = 0
        while pending and not self._stop.is_set():
            directory, depth = pending.popleft()
            for entry in self._scan(directory):
                if produced >= self._max_entries:
                    return
                if self._is_ignored(entry.name):
                    continue
                is_dir = self._is_real_directory(entry)
                yield IndexedFile(entry.path, entry.name, normalize(entry.name), is_dir, depth)
                produced += 1
                if is_dir and depth + 1 < self._max_depth:
                    pending.append((entry.path, depth + 1))

    @staticmethod
    def _scan(directory: str) -> list[os.DirEntry[str]]:
        try:
            with os.scandir(directory) as iterator:
                return list(iterator)
        except OSError:
            return []

    def _is_ignored(self, name: str) -> bool:
        return name in self._excluded or (not self._include_hidden and name.startswith("."))

    @staticmethod
    def _is_real_directory(entry: os.DirEntry[str]) -> bool:
        try:
            return entry.is_dir(follow_symlinks=False)
        except OSError:
            return False
