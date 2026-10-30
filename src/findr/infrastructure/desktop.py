import logging
from pathlib import Path

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402

logger = logging.getLogger(__name__)


class GtkDesktop:
    """``DesktopPort`` implementation backed by Gio, GTK and the freedesktop D-Bus APIs."""

    FILE_MANAGER_BUS_NAME = "org.freedesktop.FileManager1"
    FILE_MANAGER_PATH = "/org/freedesktop/FileManager1"
    DBUS_TIMEOUT_MS = 2000

    def launch_application(self, app_id: str) -> None:
        info = Gio.DesktopAppInfo.new(app_id)
        if info is None:
            raise LookupError(f"application {app_id!r} is no longer installed")
        info.launch([], self._launch_context())

    def open_uri(self, uri: str) -> None:
        Gio.AppInfo.launch_default_for_uri(uri, self._launch_context())

    def reveal_path(self, path: str) -> None:
        """Opens the containing folder with the item selected (Finder's "Show in Enclosing Folder")."""
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            bus.call_sync(
                self.FILE_MANAGER_BUS_NAME, self.FILE_MANAGER_PATH, self.FILE_MANAGER_BUS_NAME, "ShowItems",
                GLib.Variant("(ass)", ([Path(path).as_uri()], "")),
                None, Gio.DBusCallFlags.NONE, self.DBUS_TIMEOUT_MS, None,
            )
        except GLib.Error as error:
            logger.info("FileManager1 unavailable (%s); opening parent folder", error.message)
            self.open_uri(Path(path).parent.as_uri())

    def copy_text(self, text: str) -> None:
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
        clipboard.store()

    @staticmethod
    def _launch_context() -> Gio.AppLaunchContext:
        context = Gdk.Display.get_default().get_app_launch_context()
        context.set_timestamp(Gtk.get_current_event_time())
        return context
