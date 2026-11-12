# PythonPanel

<p align="center">
  <img src="pythonpanel.svg" alt="PythonPanel Logo" width="160" height="160">
</p>

A fast, modern Python IDE and code editor with **Retina Vision** (HiDPI dynamic font scaling, subpixel anti-aliasing), **Line Numbers**, **Multi-Tab Document Editing**, **Interactive Python Shell**, and **System Base Python Interpreter Execution**, built natively for **Linux Mint Cinnamon** using Python 3, GTK 3, and GtkSourceView 4.

---

## Key Features

### System Base Python Execution & Interactive Shell
- **Run Script in Base Interpreter (`F5`)**: Execute Python scripts directly using the active base interpreter (e.g. `python3.12`) with real-time unbuffered stdout/stderr streaming and interactive `stdin` input support.
- **Run with Arguments (`Shift + F5`)**: Launch scripts with custom command-line arguments parsed safely via `shlex`.
- **Interactive Python Shell**: Persistent interactive REPL session with command history (`Up`/`Down` arrows), multi-line continuation, modal `input()` prompt bridging, `SystemExit`/`KeyboardInterrupt` isolation, and shell restart (`Ctrl + F6`).
- **Interpreter Selector**: Switch seamlessly between system base Python, specific versions (`python3.12`), or virtual environments (*Menu -> Python Execution -> Select Python Interpreter*).
- **Module Syntax Verification (`Alt + X`)**: Instant syntax check using Python's built-in AST parser without running the script.

### Project File Structure Sidebar & Workspace Mode
- **Left-Hand Project Tree**: Full hierarchical file and folder view on the left side of the UI, providing traditional IDE project navigation.
- **One-Click Sidebar Toggle (`Ctrl + B` / `F9`)**: Toggle the sidebar on or off with a dedicated HeaderBar button or keyboard shortcut, allowing seamless switching between full multi-file project workflows and distraction-free, full-width editing for one-off scripts.
- **Dynamic Lazy Loading**: Subdirectories expand and collapse smoothly on demand, ensuring fast responsiveness even in large repositories.
- **File & Folder Management**: Create new files or folders, rename, delete, copy paths, or reveal in your system file manager directly from right-click context menus.
- **Smart Tab Integration**: Activating files in the tree opens them in editor tabs or focuses existing tabs without duplicates; saving files or switching tabs highlights the file in the project tree.

### Advanced Code Editing & Multi-Tab Interface
- **Multi-Tab Editing**: Work on multiple files simultaneously with individual tab modified indicators and close buttons (`Ctrl + T` / `Ctrl + N` new tab, `Ctrl + W` close tab).
- **Toggle Comments (`Ctrl + /`)**: Comment or uncomment current lines or selections with `#`.
- **Duplicate Line (`Ctrl + D`)**: Duplicate the active line or selection.
- **Delete Line (`Ctrl + Shift + K`)**: Delete the entire current line.
- **Move Lines (`Alt + Up` / `Alt + Down`)**: Shift lines up or down fluidly.
- **Join Lines (`Ctrl + J`)**: Join current line with the next.
- **Case Conversion (`Ctrl + Shift + U` / `Ctrl + U`)**: Transform selected text to UPPERCASE or lowercase.
- **Block Indentation (`Ctrl + ]` / `Ctrl + [`)**: Indent or unindent selected code blocks by 4 spaces.

### Pylint & Code Diagnostics Viewer
- **Integrated Diagnostics Table (`F8` / `Ctrl + Shift + L`)**: View all code issues categorized by Severity (Error, Warning, Refactor, Convention), Line, Column, Rule Code (e.g. `C0114`, `W0611`), and Message.
- **Click-to-Jump Navigation**: Double-click or select any diagnostic row to jump the editor cursor directly to that exact line and column.
- **Native AST Syntax Fallback**: Instant syntax error detection even if external tools are not installed.

### Retina Vision (HiDPI & Sharp Typography)
- **Dynamic Retina Zooming**: Scale font size fluidly from **50% up to 300%** using keyboard shortcuts (`Ctrl + +`, `Ctrl + -`, `Ctrl + 0`) or by holding **`Ctrl` while scrolling the mouse wheel**.
- **Cairo Subpixel Anti-Aliasing**: Fine-tuned CSS rules and Pango font descriptions preserve crisp glyph rendering on high-resolution displays (Full HD, 2K, 3K, 4K, and Apple Retina screens).
- **Scalable Vector Artwork**: High-definition SVG application icon (`pythonpanel.svg`) that scales sharply at 100%, 125%, 150%, 175%, or 200% Cinnamon desktop scaling.
- **Retina Diagnostics**: Built-in monitor resolution, display scale factor, and Cairo subpixel diagnostics dialog (*Menu -> Retina Vision / HiDPI Info*).

### Crisp Line Numbers & Navigation
- **Line Numbers Gutter**: High-contrast line numbers margin that scales proportionally with font size.
- **Active Line Highlighting**: Subtly highlights the current line to keep focus.
- **Go to Line (`Ctrl + G`)**: Instantly jump to any line in your document.
- **One-Click Toggle**: Turn line numbers on or off anytime with the headerbar toggle button.

### Integrated Search & Replace
- **Non-blocking Search Bar (`Ctrl + F`)**: Find occurrences with live match counting.
- **Full Replace (`Ctrl + H`)**: Single replace or "Replace All".
- **Advanced Match Options**: Toggle Case Sensitivity (`Aa`), Regular Expressions (`.*`), and Whole Word (`\b`).

### Themes & Customization
- **Dark Mode UI & Neon Blue Accents**: Native GTK dark mode interface featuring crisp white typography, neon cyan/blue indicators, active tab glowing accents, and custom GtkSourceView style scheme (`pythonpanel-neon`).
- **GtkSource Style Schemes**: Switch between color themes (*Menu -> Color Theme*):
  - `pythonpanel-neon` (Default: Dark mode with brilliant white text and neon blue accents)
  - `xed` (Linux Mint native look)
  - `solarized-dark` & `solarized-light` (Designed to reduce eye strain)
  - `oblivion` & `cobalt` (High-contrast dark modes)
  - `classic` & `tango` (Crisp light modes)
- **Font Selector**: Pick any installed monospace font (e.g. *DejaVu Sans Mono*, *Liberation Mono*, *Fira Code*, *JetBrains Mono*).
- **Word Wrap**: Toggleable word wrap mode (*Menu -> Word Wrap*).

### Real-Time Status Bar
- Cursor Position: `Ln X, Col Y`
- Document Metrics: `X lines, Y words, Z chars`
- Active Interpreter: `Python: 3.12.3 (Base)`
- File Format: `UTF-8 | LF`
- Retina Zoom Level: `Retina: 100%`

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
git clone https://github.com/kyledeanml/pythonpanel.git
cd pythonpanel
```

### 3. Run Installer
```bash
./install.sh
```
The installer automatically:
- Installs the high-DPI vector icon into `~/.local/share/icons/hicolor/scalable/apps/pythonpanel.svg`.
- Installs the desktop launcher with `StartupWMClass=pythonpanel` for window grouping into `~/.local/share/applications/pythonpanel.desktop`.
- Creates a CLI binary symlink at `~/.local/bin/pythonpanel`.
- Registers PythonPanel as the default application for opening `.txt` (`text/plain`) and `.py` (`text/x-python`, `text/x-python3`, `application/x-python-code`) files in Linux Mint Cinnamon / Nemo.
- Adds PythonPanel to Cinnamon's application favorites.

### 4. Put PythonPanel on the Cinnamon Panel
Once installed, you can add PythonPanel directly to your taskbar/panel:
1. Open the **Cinnamon Menu** (bottom-left corner).
2. Find **PythonPanel** (under *Programming* or *Favorites*).
3. **Right-click** PythonPanel and click **"Add to panel"**.
*(Alternatively, drag the PythonPanel icon from the menu and drop it onto the panel).*

---

## Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `F5` | **Run Script in Base Interpreter** |
| `Shift + F5` | **Run Script with Arguments** |
| `Alt + X` | **Check Module Syntax** |
| `Ctrl + F6` | **Restart Interactive Shell** |
| `F8` / `Ctrl + Shift + L` | **Run Pylint & Diagnostics Panel** |
| `Ctrl + /` | **Toggle Line Comment** |
| `Ctrl + D` | **Duplicate Line or Selection** |
| `Ctrl + Shift + K` | **Delete Current Line** |
| `Alt + Up` / `Alt + Down` | **Move Line Up / Down** |
| `Ctrl + J` | **Join Lines** |
| `Ctrl + Shift + U` / `Ctrl + U` | **Convert to UPPERCASE / lowercase** |
| `Ctrl + ]` / `Ctrl + [` | **Indent / Unindent Block** |
| `Ctrl + T` / `Ctrl + N` | **New Tab** |
| `Ctrl + W` | **Close Current Tab** |
| `Ctrl + PageUp` / `PageDown` | **Switch Tabs** |
| `Ctrl + B` / `F9` | **Toggle Project Sidebar** |
| `Ctrl + Shift + O` | **Open Project Folder** |
| `Ctrl + O` | Open File |
| `Ctrl + S` / `Ctrl + Shift + S` | Save / Save As |
| `Ctrl + F` / `Ctrl + H` | Find / Replace Bar |
| `Ctrl + G` | Go to Line |
| `Ctrl + +` / `Ctrl + -` | Retina Zoom In / Out |
| `Ctrl + 0` | Reset Retina Zoom (100%) |
| `Ctrl + Scroll Wheel` | Smooth Real-Time Zooming |
| `Ctrl + Q` | Quit Application |

---

## Linux Mint HiDPI Display Settings Tip

For high-resolution monitors on Linux Mint Cinnamon:
1. Open **System Settings -> General**.
2. Under **Desktop Scaling**, select **Auto** or **Double (HiDPI)**.
3. In PythonPanel, you can use `Ctrl + Mouse Wheel` or the zoom buttons on the HeaderBar to adjust text readability without blurring.
