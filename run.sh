#!/bin/bash
# PythonPad Launcher for Linux Mint Cinnamon
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Ensure ~/.local/bin is in PATH when launched from Cinnamon desktop menu/panel
export PATH="$HOME/.local/bin:$PATH"

# Ensure proper GDK rendering backends for HiDPI / Retina and prevent bytecode clutter
export GDK_RENDERING=similar
export PYTHONDONTWRITEBYTECODE=1

PY_BIN="/usr/bin/python3"
[ -x "$PY_BIN" ] || PY_BIN="python3"
exec "$PY_BIN" -B "$SCRIPT_DIR/pythonpad.py" "$@"
