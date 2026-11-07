#!/bin/bash
# PythonPad Launcher for Linux Mint Cinnamon
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Ensure proper GDK rendering backends for HiDPI / Retina
export GDK_RENDERING=similar

exec python3 "$SCRIPT_DIR/pythonpad.py" "$@"
