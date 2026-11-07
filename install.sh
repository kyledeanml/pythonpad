#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$HOME/.local/share/applications"
ICONS_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
BIN_DIR="$HOME/.local/bin"

echo "=========================================================="
echo " Installing PythonPad for Linux Mint Cinnamon"
echo " (Python IDE with System Base Interpreter)"
echo "=========================================================="

chmod +x "$DIR/run.sh" "$DIR/pythonpad.py"

mkdir -p "$APP_DIR"
mkdir -p "$ICONS_DIR"
mkdir -p "$BIN_DIR"

# 1. Install high-DPI vector icon
cp "$DIR/pythonpad.svg" "$ICONS_DIR/pythonpad.svg"
echo "[+] Installed PythonPad SVG icon: $ICONS_DIR/pythonpad.svg"

# 2. Install executable launcher in ~/.local/bin
ln -sf "$DIR/run.sh" "$BIN_DIR/pythonpad"
echo "[+] Created CLI executable link: $BIN_DIR/pythonpad"

# 3. Write desktop launcher for Cinnamon Menu and Panel
cat <<EOF > "$APP_DIR/pythonpad.desktop"
[Desktop Entry]
Name=PythonPad
Comment=Python IDE and code editor with Retina Vision, interactive shell, and system base Python runner
GenericName=Python IDE & Code Editor
Exec=$DIR/run.sh %F
Icon=$ICONS_DIR/pythonpad.svg
Terminal=false
Type=Application
Categories=GTK;GNOME;Development;IDE;
MimeType=text/plain;text/x-python;text/markdown;text/x-shellscript;
StartupNotify=true
StartupWMClass=pythonpad
Keywords=python;editor;ide;retina;vision;pylint;shell;repl;code;text;developer;
Actions=NewWindow;

[Desktop Action NewWindow]
Name=Open a New Window
Exec=$DIR/run.sh
EOF

chmod +x "$APP_DIR/pythonpad.desktop"
echo "[+] Installed desktop entry: $APP_DIR/pythonpad.desktop"

# Clean up older retinapad launcher if present
if [ -f "$APP_DIR/retinapad.desktop" ]; then
    rm -f "$APP_DIR/retinapad.desktop"
    echo "[+] Cleaned up previous retinapad.desktop entry"
fi

# 4. Refresh desktop database & icon caches
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DIR" || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
fi

# 5. Add to Cinnamon Menu favorites
if command -v gsettings >/dev/null 2>&1; then
    python3 -c "
import gi
from gi.repository import Gio
try:
    settings = Gio.Settings.new('org.cinnamon')
    favs = list(settings.get_strv('favorite-apps'))
    if 'retinapad.desktop' in favs:
        favs.remove('retinapad.desktop')
    if 'pythonpad.desktop' not in favs:
        favs.append('pythonpad.desktop')
    settings.set_strv('favorite-apps', favs)
    print('[+] Added PythonPad to Cinnamon favorite apps')
except Exception as e:
    pass
" || true
fi

echo ""
echo "=========================================================="
echo " Installation Complete!"
echo "=========================================================="
echo "To place PythonPad on your Linux Mint Cinnamon panel:"
echo "  1. Click your Cinnamon Menu button (bottom-left)."
echo "  2. Search for 'PythonPad' (under Programming or Favorites)."
echo "  3. Right-click 'PythonPad' and select 'Add to panel'."
echo "     (Or drag the PythonPad icon from the menu and drop"
echo "      it directly onto your panel)."
echo ""
echo "You can also launch it anytime from terminal by typing:"
echo "  pythonpad"
echo "=========================================================="
