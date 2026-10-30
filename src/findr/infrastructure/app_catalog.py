import os
from collections.abc import Sequence

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio  # noqa: E402

from findr.providers.applications import AppEntry  # noqa: E402


class GioApplicationCatalog:
    """Adapter from the desktop's ``.desktop`` entries (via Gio) to ``AppEntry`` snapshots.

    Must be created on the main thread; it reloads itself when apps are
    installed or removed (Observer via ``Gio.AppInfoMonitor``).
    """

    def __init__(self) -> None:
        self._entries: tuple[AppEntry, ...] = ()
        self.reload()
        self._monitor = Gio.AppInfoMonitor.get()
        self._monitor.connect("changed", lambda *_: self.reload())

    def entries(self) -> Sequence[AppEntry]:
        return self._entries

    def reload(self) -> None:
        unique: dict[str, AppEntry] = {}
        for info in Gio.AppInfo.get_all():
            if info.should_show() and info.get_id() and info.get_id() not in unique:
                unique[info.get_id()] = self._to_entry(info)
        self._entries = tuple(unique.values())

    @staticmethod
    def _to_entry(info: Gio.AppInfo) -> AppEntry:
        icon = info.get_icon()
        is_desktop_info = isinstance(info, Gio.DesktopAppInfo)
        return AppEntry(
            app_id=info.get_id(),
            name=info.get_display_name() or info.get_name(),
            description=info.get_description() or "",
            generic_name=(info.get_generic_name() or "") if is_desktop_info else "",
            keywords=tuple(info.get_keywords() or ()) if is_desktop_info else (),
            executable=os.path.basename(info.get_executable() or ""),
            icon=icon.to_string() if icon else None,
        )
