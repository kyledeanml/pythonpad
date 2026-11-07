#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$HOME/.local/share/applications"
ICONS_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

echo "=========================================================="
echo " Installing RetinaPad for Linux Mint Cinnamon"
echo "=========================================================="

chmod +x "$DIR/run.sh" "$DIR/retinapad.py"

mkdir -p "$APP_DIR"
mkdir -p "$ICONS_DIR"

# Install scalable icon
cp "$DIR/retinapad.svg" "$ICONS_DIR/retinapad.svg"

# Write desktop launcher with correct paths
cat <<EOF > "$APP_DIR/retinapad.desktop"
[Desktop Entry]
Name=RetinaPad
Comment=Simple notepad with retina vision and line numbers for Linux Mint Cinnamon
GenericName=Text Editor
Exec=$DIR/run.sh %F
Icon=$ICONS_DIR/retinapad.svg
Terminal=false
Type=Application
Categories=GTK;GNOME;Utility;TextEditor;
MimeType=text/plain;text/x-python;text/markdown;text/x-shellscript;
StartupNotify=true
Keywords=text;editor;notepad;retina;vision;notes;mint;cinnamon;
Actions=NewWindow;

[Desktop Action NewWindow]
Name=Open a New Window
Exec=$DIR/run.sh
EOF

chmod +x "$APP_DIR/retinapad.desktop"

# Refresh desktop database if available
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DIR" || true
fi

echo "✓ RetinaPad successfully installed!"
echo "✓ Desktop entry created: $APP_DIR/retinapad.desktop"
echo "✓ You can find RetinaPad in Cinnamon Menu -> Accessories -> RetinaPad"
echo "✓ Or launch it from terminal anytime with: $DIR/run.sh"
