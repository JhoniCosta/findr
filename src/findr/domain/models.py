from dataclasses import dataclass
from enum import Enum

from findr.domain.actions import Action


class ResultKind(Enum):
    CALCULATION = "calculation"
    APPLICATION = "application"
    FOLDER = "folder"
    FILE = "file"
    WEB = "web"


@dataclass(frozen=True, slots=True)
class SearchResult:
    """A single entry shown in the result list.

    ``id`` is a stable identity used for de-duplication and usage history.
    ``icon`` is a string understood by ``Gio.Icon.new_for_string`` (see ``domain.icons``).
    ``score`` is the relevance in [0, 1+]; higher is better.
    """

    id: str
    title: str
    subtitle: str
    kind: ResultKind
    score: float
    action: Action
    alternate_action: Action | None = None
    icon: str | None = None


@dataclass(frozen=True, slots=True)
class ResultGroup:
    """A section of the result list. ``kind`` is ``None`` for the "top hit" section."""

    kind: ResultKind | None
    results: tuple[SearchResult, ...]

    @property
    def is_top_hit(self) -> bool:
        return self.kind is None
