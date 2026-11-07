#!/bin/bash
# PythonPad Launcher for Linux Mint Cinnamon
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Ensure proper GDK rendering backends for HiDPI / Retina and prevent bytecode clutter
export GDK_RENDERING=similar
export PYTHONDONTWRITEBYTECODE=1

exec python3 -B "$SCRIPT_DIR/pythonpad.py" "$@"
