#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$HOME/.local/share/applications"
ICONS_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
BIN_DIR="$HOME/.local/bin"
STYLES_DIR="$HOME/.local/share/gtksourceview-4/styles"

echo "=========================================================="
echo " Installing PythonPad for Linux Mint Cinnamon"
echo " (Python IDE with System Base Interpreter)"
echo "=========================================================="

chmod +x "$DIR/run.sh" "$DIR/pythonpad.py"

mkdir -p "$APP_DIR"
mkdir -p "$ICONS_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$STYLES_DIR"

# 1. Install high-DPI vector icon & multi-size PNG icons for Cinnamon panel / menus
cp -f "$DIR/pythonpad.svg" "$ICONS_DIR/pythonpad.svg"
mkdir -p "$HOME/.icons" "$HOME/.local/share/pixmaps"
cp -f "$DIR/pythonpad.svg" "$HOME/.icons/pythonpad.svg"
cp -f "$DIR/pythonpad.svg" "$HOME/.local/share/pixmaps/pythonpad.svg"

python3 -B -c "
import os, gi
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import GdkPixbuf
src = '$DIR/pythonpad.svg'
base = os.path.expanduser('~/.local/share/icons/hicolor')
for sz in (16, 24, 32, 48, 64, 128, 256, 512):
    out_dir = os.path.join(base, f'{sz}x{sz}', 'apps')
    os.makedirs(out_dir, exist_ok=True)
    pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(src, sz, sz, True)
    pb.savev(os.path.join(out_dir, 'pythonpad.png'), 'png', [], [])
" 2>/dev/null || true

echo "[+] Installed PythonPad SVG & panel icon set: $ICONS_DIR/pythonpad.svg"
if [ -d "$DIR/styles" ]; then
    cp -r "$DIR/styles/"* "$STYLES_DIR/"
    echo "[+] Installed GtkSource style schemes: $STYLES_DIR"
fi

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
Categories=GTK;GNOME;Development;IDE;Utility;TextEditor;
MimeType=text/plain;text/x-python;text/x-python3;application/x-python-code;text/markdown;text/x-shellscript;
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

# 5. Register PythonPad as the default application for .txt and .py files
DEFAULT_MIMES=(
    "text/plain"
    "text/x-python"
    "text/x-python3"
    "application/x-python-code"
)

if command -v xdg-mime >/dev/null 2>&1; then
    for mime in "${DEFAULT_MIMES[@]}"; do
        xdg-mime default pythonpad.desktop "$mime" 2>/dev/null || true
    done
    echo "[+] Registered PythonPad via xdg-mime as default handler for .txt and .py files"
fi

if command -v gio >/dev/null 2>&1; then
    for mime in "${DEFAULT_MIMES[@]}"; do
        gio mime "$mime" pythonpad.desktop >/dev/null 2>&1 || true
    done
fi

# Ensure ~/.config/mimeapps.list explicitly maps .txt and .py MIME types for Cinnamon / Nemo
python3 -c "
import os
import configparser

mimeapps_path = os.path.expanduser('~/.config/mimeapps.list')
os.makedirs(os.path.dirname(mimeapps_path), exist_ok=True)

cfg = configparser.ConfigParser(interpolation=None)
cfg.optionxform = str
if os.path.exists(mimeapps_path):
    try:
        cfg.read(mimeapps_path, encoding='utf-8')
    except Exception:
        pass

for section in ('Default Applications', 'Added Associations'):
    if not cfg.has_section(section):
        cfg.add_section(section)
    for mime in ('text/plain', 'text/x-python', 'text/x-python3', 'application/x-python-code'):
        cfg.set(section, mime, 'pythonpad.desktop;')

with open(mimeapps_path, 'w', encoding='utf-8') as f:
    cfg.write(f, space_around_delimiters=False)
" 2>/dev/null || true

# 6. Enable direct execution/opening in Nemo when double-clicking .py/.txt files
#    and add to Cinnamon Menu favorites
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
