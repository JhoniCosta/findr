#!/bin/sh
# Removes Findr and restores the shortcuts it had released (e.g. GNOME's Alt+Space window menu).
set -u

PREFIX="${XDG_DATA_HOME:-$HOME/.local/share}/findr"
BIN_DIR="$HOME/.local/bin"

[ -x "$BIN_DIR/findr" ] && "$BIN_DIR/findr" --uninstall-hotkey
[ -x "$BIN_DIR/findr" ] && "$BIN_DIR/findr" --quit >/dev/null 2>&1

rm -f "$BIN_DIR/findr" "$BIN_DIR/findr-toggle" \
      "${XDG_DATA_HOME:-$HOME/.local/share}/applications/io.github.findr.Findr.desktop" \
      "${XDG_CONFIG_HOME:-$HOME/.config}/autostart/findr.desktop"
rm -rf "$PREFIX/src" "$PREFIX/bin"

echo "Findr removido. Histórico de uso mantido em $PREFIX (apague manualmente se quiser)."
