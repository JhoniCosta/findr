#!/bin/sh
# Installs Findr for the current user (no root, no pip: uses the system's python3-gi).
set -eu

PREFIX="${XDG_DATA_HOME:-$HOME/.local/share}/findr"
BIN_DIR="$HOME/.local/bin"
APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
SOURCE_DIR=$(dirname "$(readlink -f "$0")")

python3 -c "import gi; gi.require_version('Gtk', '3.0')" 2>/dev/null || {
    echo "Dependência ausente. Instale com: sudo apt install python3-gi gir1.2-gtk-3.0" >&2
    exit 1
}

echo "→ Copiando arquivos para $PREFIX"
mkdir -p "$PREFIX" "$BIN_DIR" "$APPS_DIR" "$AUTOSTART_DIR"
rm -rf "$PREFIX/src" "$PREFIX/bin"
cp -r "$SOURCE_DIR/src" "$SOURCE_DIR/bin" "$PREFIX/"
find "$PREFIX/src" -name '__pycache__' -type d -prune -exec rm -rf {} +

ln -sf "$PREFIX/bin/findr" "$BIN_DIR/findr"
ln -sf "$PREFIX/bin/findr-toggle" "$BIN_DIR/findr-toggle"

echo "→ Registrando entrada de menu e início automático"
sed "s|^Exec=findr|Exec=$BIN_DIR/findr|" "$SOURCE_DIR/data/io.github.findr.Findr.desktop" \
    > "$APPS_DIR/io.github.findr.Findr.desktop"
sed "s|^Exec=findr|Exec=$BIN_DIR/findr|" "$SOURCE_DIR/data/findr-autostart.desktop" \
    > "$AUTOSTART_DIR/findr.desktop"

echo "→ Registrando atalho global"
"$BIN_DIR/findr" --install-hotkey

echo "→ Iniciando em segundo plano"
"$BIN_DIR/findr" --quit >/dev/null 2>&1 || true
nohup "$BIN_DIR/findr" --daemon >/dev/null 2>&1 &

echo "Pronto! Pressione Alt+Space para abrir a barra de busca."
