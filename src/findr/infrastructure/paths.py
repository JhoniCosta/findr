"""XDG base directories used by Findr."""

import os
from pathlib import Path


def _xdg_dir(variable: str, fallback: str) -> Path:
    value = os.environ.get(variable)
    return Path(value) if value and os.path.isabs(value) else Path.home() / fallback


def config_dir() -> Path:
    return _xdg_dir("XDG_CONFIG_HOME", ".config") / "findr"


def data_dir() -> Path:
    return _xdg_dir("XDG_DATA_HOME", ".local/share") / "findr"
