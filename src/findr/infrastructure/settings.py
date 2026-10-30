import dataclasses
import logging
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_EXCLUDED_DIRS = frozenset({
    "node_modules", "__pycache__", "venv", ".venv", "site-packages", "dist", "build",
    "target", "snap", "Trash", "vendor", ".git",
})


@dataclass(frozen=True)
class Settings:
    """User-tunable options, read from ``~/.config/findr/config.toml``."""

    hotkey: str = "<Alt>space"
    max_results_per_kind: int = 6
    file_roots: tuple[str, ...] = field(default_factory=lambda: (str(Path.home()),))
    excluded_dirs: frozenset[str] = DEFAULT_EXCLUDED_DIRS
    include_hidden_files: bool = False
    max_index_depth: int = 7
    max_indexed_entries: int = 250_000
    index_refresh_minutes: int = 10
    web_search_url: str = "https://duckduckgo.com/?q={query}"
    hide_on_focus_loss: bool = True
    overlay: bool = True


class SettingsLoader:
    """Merges the TOML file over the defaults; invalid entries are reported and ignored."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> Settings:
        defaults = Settings()
        try:
            with self._path.open("rb") as stream:
                raw = tomllib.load(stream)
        except FileNotFoundError:
            return defaults
        except (OSError, tomllib.TOMLDecodeError) as error:
            logger.warning("ignoring unreadable config %s: %s", self._path, error)
            return defaults
        return dataclasses.replace(defaults, **self._valid_overrides(defaults, raw))

    def _valid_overrides(self, defaults: Settings, raw: dict[str, Any]) -> dict[str, Any]:
        overrides: dict[str, Any] = {}
        for key, value in raw.items():
            if not hasattr(defaults, key):
                logger.warning("unknown config key %r", key)
                continue
            coerced = self._coerce(getattr(defaults, key), value)
            if coerced is None:
                logger.warning("invalid value for %r: %r", key, value)
                continue
            overrides[key] = coerced
        return overrides

    @staticmethod
    def _coerce(default: Any, value: Any) -> Any:
        if isinstance(default, bool):
            return value if isinstance(value, bool) else None
        if isinstance(default, int):
            return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None
        if isinstance(default, str):
            return value if isinstance(value, str) and value else None
        if isinstance(default, (tuple, frozenset)) and isinstance(value, list):
            if not all(isinstance(item, str) for item in value):
                return None
            items = [str(Path(item).expanduser()) for item in value] if isinstance(default, tuple) else value
            return type(default)(items)
        return None
