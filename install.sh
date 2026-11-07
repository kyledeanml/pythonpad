#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$HOME/.local/share/applications"
ICONS_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
BIN_DIR="$HOME/.local/bin"

echo "=========================================================="
echo " Installing RetinaPad for Linux Mint Cinnamon"
echo "=========================================================="

chmod +x "$DIR/run.sh" "$DIR/retinapad.py"

mkdir -p "$APP_DIR"
mkdir -p "$ICONS_DIR"
mkdir -p "$BIN_DIR"

# 1. Install high-DPI vector icon
cp "$DIR/retinapad.svg" "$ICONS_DIR/retinapad.svg"
echo "[+] Installed Retina SVG icon: $ICONS_DIR/retinapad.svg"

# 2. Install executable launcher in ~/.local/bin
ln -sf "$DIR/run.sh" "$BIN_DIR/retinapad"
echo "[+] Created CLI executable link: $BIN_DIR/retinapad"

# 3. Write desktop launcher with correct paths and StartupWMClass for Cinnamon panel grouping
cat <<EOF > "$APP_DIR/retinapad.desktop"
[Desktop Entry]
Name=RetinaPad
Comment=Simple notepad with retina vision, line numbers, and pylint viewer for Linux Mint Cinnamon
GenericName=Text & Python Editor
Exec=$DIR/run.sh %F
Icon=$ICONS_DIR/retinapad.svg
Terminal=false
Type=Application
Categories=GTK;GNOME;Utility;TextEditor;
MimeType=text/plain;text/x-python;text/markdown;text/x-shellscript;
StartupNotify=true
StartupWMClass=retinapad
Keywords=text;editor;notepad;retina;vision;notes;mint;cinnamon;python;pylint;code;
Actions=NewWindow;

[Desktop Action NewWindow]
Name=Open a New Window
Exec=$DIR/run.sh
EOF

chmod +x "$APP_DIR/retinapad.desktop"
echo "[+] Installed desktop entry: $APP_DIR/retinapad.desktop"

# 4. Refresh desktop database & icon caches
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DIR" || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
fi

# 5. Add to Cinnamon Menu favorites if gsettings is available
if command -v gsettings >/dev/null 2>&1; then
    python3 -c "
import gi
from gi.repository import Gio
try:
    settings = Gio.Settings.new('org.cinnamon')
    favs = list(settings.get_strv('favorite-apps'))
    if 'retinapad.desktop' not in favs:
        favs.append('retinapad.desktop')
        settings.set_strv('favorite-apps', favs)
        print('[+] Added RetinaPad to Cinnamon favorite apps')
except Exception as e:
    pass
" || true
fi

echo ""
echo "=========================================================="
echo " Installation Complete!"
echo "=========================================================="
echo "To place RetinaPad on your Linux Mint Cinnamon panel:"
echo "  1. Click your Cinnamon Menu button (bottom-left)."
echo "  2. Search for 'RetinaPad' (under Accessories or Favorites)."
echo "  3. Right-click 'RetinaPad' and select 'Add to panel'."
echo "     (Alternatively, drag the RetinaPad icon from the menu"
echo "      and drop it directly onto your panel)."
echo ""
echo "You can also launch it anytime from terminal by typing:"
echo "  retinapad"
echo "=========================================================="
