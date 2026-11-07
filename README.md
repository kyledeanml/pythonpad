# RetinaPad

A simple, fast, and elegant Notepad with **Retina Vision** (HiDPI dynamic font scaling, subpixel anti-aliasing), **Line Numbers**, and an integrated **Pylint Viewer & Native Python Runner**, built natively for **Linux Mint Cinnamon** using Python 3, GTK 3, and GtkSourceView 4.

---

## Key Features

### Native Python Compatibility & Pylint Viewer
- **Integrated Pylint Diagnostics**: Run Pylint analysis with one click or shortcut (`F8` / `Ctrl + Shift + L`). Shows severity (Error, Warning, Refactor, Convention), line, column, rule code (e.g. `C0114`, `W0611`), and full message.
- **Click-to-Jump Navigation**: Double-click or select any diagnostic row to jump the cursor immediately to that exact line and column in the editor.
- **Native Python AST Syntax Checker**: Instant syntax error detection powered by Python's built-in AST parser, providing accurate syntax diagnostics even without external dependencies.
- **Native Python Script Runner (`F5`)**: Execute Python scripts directly inside an integrated console panel with live stdout/stderr color streams and process stop controls.
- **Python Syntax Highlighting & Indentation**: Full language highlighting, smart 4-space tab indentation, and matching bracket highlights.

### Retina Vision (HiDPI & Sharp Typography)
- **Dynamic Retina Zooming**: Scale the text size fluidly from **50% up to 300%** using keyboard shortcuts (`Ctrl + +`, `Ctrl + -`, `Ctrl + 0`) or by holding **`Ctrl` while scrolling the mouse wheel**.
- **Cairo Subpixel Anti-Aliasing**: Fine-tuned CSS rules and Pango font descriptions preserve crisp glyph rendering on high-resolution displays (Full HD, 2K, 3K, 4K, and Apple Retina screens).
- **Scalable Vector Artwork**: High-definition SVG application icon (`retinapad.svg`) that scales sharply at 100%, 125%, 150%, 175%, or 200% Cinnamon desktop scaling.
- **Retina Diagnostics**: Built-in monitor resolution, display scale factor, and Cairo subpixel diagnostics dialog (*Menu -> Retina Vision / HiDPI Info*).

### Crisp Line Numbers & Navigation
- **Line Numbers Gutter**: High-contrast, beautifully padded line numbers margin that scales proportionally with the font size.
- **Active Line Highlighting**: Subtly highlights the current line to keep focus.
- **Go to Line (`Ctrl + G`)**: Instantly jump to any line in your document.
- **One-Click Toggle**: Turn line numbers on or off anytime with the headerbar toggle button.

### Integrated Search & Replace
- **Non-blocking Search Bar (`Ctrl + F`)**: Find occurrences with live match counting.
- **Full Replace (`Ctrl + H`)**: Single replace or "Replace All".
- **Advanced Match Options**: Toggle Case Sensitivity (`Aa`), Regular Expressions (`.*`), and Whole Word (`\b`).

### Themes & Customization
- **Native Cinnamon Themes**: Switch between pre-installed GtkSource schemes:
  - `xed` (Linux Mint native look)
  - `solarized-dark` & `solarized-light` (Designed to reduce eye strain)
  - `oblivion` & `cobalt` (High-contrast dark modes)
  - `classic` & `tango` (Crisp light modes)
- **Font Selector**: Pick any installed monospace font (e.g. *DejaVu Sans Mono*, *Liberation Mono*, *Fira Code*, *JetBrains Mono*).
- **Word Wrap**: Toggleable word wrap mode (*Menu -> Word Wrap*).

### Real-Time Status Bar
- Cursor Position: `Ln X, Col Y`
- Document Metrics: `X lines, Y words, Z chars`
- Retina Zoom Level: `Retina: 100%`
- Character Encoding: `UTF-8`

---

## Installation & Adding to Cinnamon Panel

### 1. Install System Dependencies
On Linux Mint or Ubuntu-based distributions:
```bash
sudo apt update
sudo apt install python3 python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-gtksource-4 pylint
```

### 2. Clone Repository
```bash
git clone https://github.com/kyledeanml/retina-notepad.git
cd retina-notepad
```

### 3. Run Installer
```bash
./install.sh
```
The installer automatically:
- Installs the high-DPI vector icon into `~/.local/share/icons/hicolor/scalable/apps/`.
- Installs the desktop launcher with `StartupWMClass=retinapad` for window grouping into `~/.local/share/applications/`.
- Creates a CLI binary symlink at `~/.local/bin/retinapad`.
- Adds RetinaPad to Cinnamon's application favorites.

### 4. Put RetinaPad on the Cinnamon Panel
Once installed, you can add RetinaPad directly to your taskbar/panel:
1. Open the **Cinnamon Menu** (bottom-left corner).
2. Find **RetinaPad** (under *Accessories* or *Programming*).
3. **Right-click** RetinaPad and click **"Add to panel"**.
*(Alternatively, drag the RetinaPad icon from the menu and drop it onto the panel).*

---

## Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `F5` | **Run Python Script** (in bottom console) |
| `F8` / `Ctrl + Shift + L` | **Run Pylint & Diagnostics Panel** |
| `Ctrl + N` | New Document |
| `Ctrl + O` | Open File |
| `Ctrl + S` | Save File |
| `Ctrl + Shift + S` | Save As |
| `Ctrl + F` | Find |
| `Ctrl + H` | Find and Replace |
| `Ctrl + G` | Go to Line |
| `Ctrl + +` / `Ctrl + =` | **Retina Zoom In** |
| `Ctrl + -` | **Retina Zoom Out** |
| `Ctrl + 0` | **Reset Retina Zoom (100%)** |
| `Ctrl + Scroll Wheel` | **Smooth Retina Zooming** |
| `Ctrl + Z` | Undo |
| `Ctrl + Y` | Redo |
| `Ctrl + W` / `Ctrl + Q` | Close / Quit |

---

## Linux Mint HiDPI Display Settings Tip

For high-resolution monitors on Linux Mint Cinnamon:
1. Open **System Settings -> General**.
2. Under **Desktop Scaling**, select **Auto** or **Double (HiDPI)**.
3. In RetinaPad, you can use `Ctrl + Mouse Wheel` or the zoom buttons on the HeaderBar to adjust text readability without blurring.
