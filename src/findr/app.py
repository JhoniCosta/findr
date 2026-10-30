"""Composition root: wires the object graph and maps the command line to GActions.

Findr runs as a single-instance ``Gtk.Application``. Later invocations
(``findr --toggle``) are forwarded over D-Bus to the running instance, and
``bin/findr-toggle`` calls the exported ``toggle`` action directly.
"""

import logging
import shutil
import sys
from pathlib import Path

import findr.ui  # noqa: F401  (pins the GTK version before importing Gtk)
from gi.repository import Gio, GLib, Gtk

from findr import APP_ID, __version__
from findr.domain.matching import FuzzyMatcher
from findr.infrastructure.app_catalog import GioApplicationCatalog
from findr.infrastructure.desktop import GtkDesktop
from findr.infrastructure.file_index import FileSystemIndex
from findr.infrastructure.gnome_hotkey import GnomeHotkeyRegistrar, HotkeyUnsupportedError
from findr.infrastructure.paths import config_dir, data_dir
from findr.infrastructure.settings import Settings, SettingsLoader
from findr.infrastructure.usage_store import JsonUsageRepository
from findr.providers.applications import ApplicationProvider
from findr.providers.calculator import CalculatorProvider
from findr.providers.files import FileProvider
from findr.providers.web import WebSearchProvider
from findr.services.grouping import ResultGrouper
from findr.services.ranking import UsageAwareRanking
from findr.services.search_engine import SearchEngine
from findr.ui.controller import SearchController
from findr.ui.window import LauncherWindow

logger = logging.getLogger(__name__)


class FindrApplication(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self._settings: Settings = SettingsLoader(config_dir() / "config.toml").load()
        self._window: LauncherWindow | None = None
        self._controller: SearchController | None = None
        self._file_index: FileSystemIndex | None = None
        self._register_options()

    # ----- Lifecycle ------------------------------------------------------

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)
        self._build_object_graph()
        self._register_actions()
        self.hold()  # Stay resident while the window is hidden, like Spotlight.

    def do_shutdown(self) -> None:
        if self._controller:
            self._controller.shutdown()
        if self._file_index:
            self._file_index.stop()
        Gtk.Application.do_shutdown(self)

    def do_activate(self) -> None:
        self.activate_action("show", None)

    def do_handle_local_options(self, options: GLib.VariantDict) -> int:
        # ``contains`` instead of ``end()``: ending the dict would invalidate the
        # options GApplication still has to forward to the primary instance.
        if options.contains("version"):
            print(f"findr {__version__}")
            return 0
        if options.contains("install-hotkey"):
            return self._install_hotkey()
        if options.contains("uninstall-hotkey"):
            return self._uninstall_hotkey()
        return -1  # Continue: register on the bus and forward to the primary instance.

    def do_command_line(self, command_line: Gio.ApplicationCommandLine) -> int:
        options = command_line.get_options_dict()
        for option in ("quit", "hide", "toggle", "daemon"):
            if options.contains(option):
                if option != "daemon":
                    self.activate_action(option, None)
                return 0
        self.activate_action("show", None)
        return 0

    # ----- Wiring ---------------------------------------------------------

    def _build_object_graph(self) -> None:
        settings = self._settings
        matcher = FuzzyMatcher()
        usage = JsonUsageRepository(data_dir() / "usage.json")

        self._file_index = FileSystemIndex(
            roots=settings.file_roots,
            excluded_names=settings.excluded_dirs,
            max_depth=settings.max_index_depth,
            max_entries=settings.max_indexed_entries,
            include_hidden=settings.include_hidden_files,
        )
        self._file_index.start_background_refresh(settings.index_refresh_minutes * 60)

        engine = SearchEngine(
            providers=[
                CalculatorProvider(),
                ApplicationProvider(GioApplicationCatalog(), matcher),
                FileProvider(self._file_index, matcher, max_results=settings.max_results_per_kind * 2),
                WebSearchProvider(settings.web_search_url),
            ],
            ranking=UsageAwareRanking(usage),
            grouper=ResultGrouper(max_per_kind=settings.max_results_per_kind),
        )
        self._controller = SearchController(engine, GtkDesktop(), usage)
        self._window = LauncherWindow(
            self, self._controller, overlay=settings.overlay, hide_on_focus_loss=settings.hide_on_focus_loss
        )

    def _register_actions(self) -> None:
        handlers = {
            "show": self._window.summon,
            "hide": self._window.dismiss,
            "toggle": self._window.toggle,
            "quit": self.quit,
        }
        for name, handler in handlers.items():
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda _action, _param, run=handler: run())
            self.add_action(action)

    def _register_options(self) -> None:
        options = (
            ("toggle", "Mostra ou esconde a barra de busca"),
            ("hide", "Esconde a barra de busca"),
            ("daemon", "Inicia em segundo plano, sem mostrar a barra"),
            ("quit", "Encerra a instância em execução"),
            ("install-hotkey", "Registra o atalho global (Alt+Space) no GNOME"),
            ("uninstall-hotkey", "Remove o atalho global e restaura os atalhos liberados"),
            ("version", "Mostra a versão"),
        )
        for long_name, description in options:
            self.add_main_option(long_name, 0, GLib.OptionFlags.NONE, GLib.OptionArg.NONE, description, None)

    # ----- Hotkey ---------------------------------------------------------

    def _install_hotkey(self) -> int:
        command = self._toggle_command()
        try:
            released = GnomeHotkeyRegistrar(data_dir() / "released-shortcuts.json").install(
                self._settings.hotkey, command
            )
        except HotkeyUnsupportedError as error:
            print(error, file=sys.stderr)
            return 1
        print(f"Atalho {self._settings.hotkey} → {command}")
        for shortcut in released:
            print(f"  liberado de: {shortcut} (restaurável com --uninstall-hotkey)")
        return 0

    def _uninstall_hotkey(self) -> int:
        try:
            GnomeHotkeyRegistrar(data_dir() / "released-shortcuts.json").uninstall()
        except HotkeyUnsupportedError as error:
            print(error, file=sys.stderr)
            return 1
        print("Atalho removido e atalhos originais restaurados.")
        return 0

    @staticmethod
    def _toggle_command() -> str:
        bundled = Path(__file__).resolve().parents[2] / "bin" / "findr-toggle"
        return str(bundled) if bundled.exists() else (shutil.which("findr-toggle") or "findr-toggle")
