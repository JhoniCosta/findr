import json
import logging
import os
import tempfile
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


class JsonUsageRepository:
    """Persists ``{result_id: open_count}`` as JSON. Thread-safe; writes are atomic."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._counts = self._load()

    def usage_count(self, result_id: str) -> int:
        with self._lock:
            return self._counts.get(result_id, 0)

    def record_usage(self, result_id: str) -> None:
        with self._lock:
            self._counts[result_id] = self._counts.get(result_id, 0) + 1
            snapshot = dict(self._counts)
        self._save(snapshot)

    def _load(self) -> dict[str, int]:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, ValueError) as error:
            logger.warning("discarding unreadable usage history %s: %s", self._path, error)
            return {}
        if not isinstance(data, dict):
            return {}
        return {key: value for key, value in data.items() if isinstance(key, str) and isinstance(value, int)}

    def _save(self, counts: dict[str, int]) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_path = tempfile.mkstemp(dir=self._path.parent, prefix=".usage-", suffix=".json")
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(counts, stream)
            os.replace(temp_path, self._path)
        except OSError as error:
            logger.warning("could not save usage history: %s", error)
