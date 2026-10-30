"""Command pattern: each search result carries the action(s) it triggers.

Actions are plain data; the side effects are delegated to a ``DesktopPort``
implementation, which keeps the domain free from GTK/Gio.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Protocol


class DesktopPort(Protocol):
    """Desktop capabilities the actions depend on (Dependency Inversion)."""

    def launch_application(self, app_id: str) -> None: ...

    def open_uri(self, uri: str) -> None: ...

    def reveal_path(self, path: str) -> None: ...

    def copy_text(self, text: str) -> None: ...


class Action(ABC):
    label: ClassVar[str]

    @abstractmethod
    def execute(self, desktop: DesktopPort) -> None: ...


@dataclass(frozen=True, slots=True)
class LaunchApplication(Action):
    label: ClassVar[str] = "Abrir"
    app_id: str

    def execute(self, desktop: DesktopPort) -> None:
        desktop.launch_application(self.app_id)


@dataclass(frozen=True, slots=True)
class OpenUri(Action):
    label: ClassVar[str] = "Abrir"
    uri: str

    def execute(self, desktop: DesktopPort) -> None:
        desktop.open_uri(self.uri)


@dataclass(frozen=True, slots=True)
class OpenPath(Action):
    label: ClassVar[str] = "Abrir"
    path: str

    def execute(self, desktop: DesktopPort) -> None:
        desktop.open_uri(Path(self.path).as_uri())


@dataclass(frozen=True, slots=True)
class RevealPath(Action):
    label: ClassVar[str] = "Mostrar na pasta"
    path: str

    def execute(self, desktop: DesktopPort) -> None:
        desktop.reveal_path(self.path)


@dataclass(frozen=True, slots=True)
class CopyText(Action):
    label: ClassVar[str] = "Copiar"
    text: str

    def execute(self, desktop: DesktopPort) -> None:
        desktop.copy_text(self.text)
