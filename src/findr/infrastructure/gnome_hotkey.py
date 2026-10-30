"""Registers the global shortcut as a GNOME custom keybinding.

On Wayland an application cannot grab global keys itself, so the reliable way
is to let GNOME own the shortcut and have it run ``findr-toggle``, which
pokes the running instance over D-Bus.

Shortcuts that already use the same accelerator (on GNOME, ``<Alt>space``
opens the window menu) are released first and backed up, so ``uninstall``
can restore them.
"""

import json
import logging
from pathlib import Path

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

logger = logging.getLogger(__name__)


class HotkeyUnsupportedError(RuntimeError):
    pass


class GnomeHotkeyRegistrar:
    MEDIA_KEYS_SCHEMA = "org.gnome.settings-daemon.plugins.media-keys"
    CUSTOM_BINDING_SCHEMA = f"{MEDIA_KEYS_SCHEMA}.custom-keybinding"
    CUSTOM_BINDINGS_KEY = "custom-keybindings"
    BINDING_PATH = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/findr/"
    CONFLICT_SCHEMAS = (
        "org.gnome.desktop.wm.keybindings",
        "org.gnome.shell.keybindings",
        "org.gnome.mutter.keybindings",
    )

    def __init__(self, backup_file: Path) -> None:
        self._backup_file = backup_file
        self._schemas = Gio.SettingsSchemaSource.get_default()

    def is_supported(self) -> bool:
        return self._schemas is not None and self._schemas.lookup(self.CUSTOM_BINDING_SCHEMA, True) is not None

    def install(self, accelerator: str, command: str) -> list[str]:
        """Binds ``accelerator`` to ``command``; returns the conflicting shortcuts it released."""
        self._require_support()
        released = self._release_conflicts(accelerator)

        binding = Gio.Settings.new_with_path(self.CUSTOM_BINDING_SCHEMA, self.BINDING_PATH)
        binding.set_string("name", "Findr — barra de busca")
        binding.set_string("command", command)
        binding.set_string("binding", accelerator)

        media_keys = Gio.Settings.new(self.MEDIA_KEYS_SCHEMA)
        paths = list(media_keys.get_strv(self.CUSTOM_BINDINGS_KEY))
        if self.BINDING_PATH not in paths:
            media_keys.set_strv(self.CUSTOM_BINDINGS_KEY, [*paths, self.BINDING_PATH])

        Gio.Settings.sync()
        return released

    def uninstall(self) -> None:
        self._require_support()
        media_keys = Gio.Settings.new(self.MEDIA_KEYS_SCHEMA)
        paths = [path for path in media_keys.get_strv(self.CUSTOM_BINDINGS_KEY) if path != self.BINDING_PATH]
        media_keys.set_strv(self.CUSTOM_BINDINGS_KEY, paths)

        binding = Gio.Settings.new_with_path(self.CUSTOM_BINDING_SCHEMA, self.BINDING_PATH)
        for key in ("name", "command", "binding"):
            binding.reset(key)

        self._restore_conflicts()
        Gio.Settings.sync()

    def _require_support(self) -> None:
        if not self.is_supported():
            raise HotkeyUnsupportedError(
                "GNOME custom keybindings are not available; bind your desktop's shortcut to `findr-toggle`."
            )

    def _release_conflicts(self, accelerator: str) -> list[str]:
        backup = self._read_backup()
        released: list[str] = []
        for schema_id, settings, key in self._string_list_keys():
            values = list(settings.get_strv(key))
            if accelerator not in values:
                continue
            backup.setdefault(f"{schema_id}::{key}", values)
            settings.set_strv(key, [value for value in values if value != accelerator])
            released.append(f"{schema_id} {key}")
        self._write_backup(backup)
        return released

    def _restore_conflicts(self) -> None:
        for qualified_key, values in self._read_backup().items():
            schema_id, _, key = qualified_key.partition("::")
            if self._schemas.lookup(schema_id, True) is not None:
                Gio.Settings.new(schema_id).set_strv(key, values)
        self._backup_file.unlink(missing_ok=True)

    def _string_list_keys(self):
        for schema_id in self.CONFLICT_SCHEMAS:
            schema = self._schemas.lookup(schema_id, True)
            if schema is None:
                continue
            settings = Gio.Settings.new(schema_id)
            for key in schema.list_keys():
                if schema.get_key(key).get_value_type().equal(GLib.VariantType.new("as")):
                    yield schema_id, settings, key

    def _read_backup(self) -> dict[str, list[str]]:
        try:
            return json.loads(self._backup_file.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            return {}

    def _write_backup(self, backup: dict[str, list[str]]) -> None:
        if backup:
            self._backup_file.parent.mkdir(parents=True, exist_ok=True)
            self._backup_file.write_text(json.dumps(backup, indent=2), encoding="utf-8")
