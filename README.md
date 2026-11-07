# RetinaPad 📝👁️

A simple, fast, and elegant Notepad with **Retina Vision** (HiDPI dynamic font scaling, subpixel anti-aliasing) and **Line Numbers**, built natively for **Linux Mint Cinnamon** using Python 3, GTK 3, and GtkSourceView 4.

---

## 🌟 Key Features

### 👁️ Retina Vision (HiDPI & Sharp Typography)
- **Dynamic Retina Zooming**: Scale the text size fluidly from **50% up to 300%** using keyboard shortcuts (`Ctrl + +`, `Ctrl + -`, `Ctrl + 0`) or by holding **`Ctrl` while scrolling the mouse wheel**.
- **Cairo Subpixel Anti-Aliasing**: Fine-tuned CSS rules and Pango font descriptions preserve crisp glyph rendering on high-resolution displays (Full HD, 2K, 3K, 4K, and Apple Retina screens).
- **Scalable Vector Artwork**: High-definition SVG application icon (`retinapad.svg`) that scales sharply at 100%, 125%, 150%, 175%, or 200% Cinnamon desktop scaling.
- **Retina Diagnostics**: Built-in monitor resolution, display scale factor, and Cairo subpixel diagnostics dialog (*Menu → Retina Vision / HiDPI Info*).

### 🔢 Crisp Line Numbers & Navigation
- **Line Numbers Gutter**: High-contrast, beautifully padded line numbers margin that scales proportionally with the font size.
- **Active Line Highlighting**: Subtly highlights the current line to keep your focus.
- **Go to Line (`Ctrl + G`)**: Instantly jump to any line in your document.
- **One-Click Toggle**: Turn line numbers on or off anytime with the headerbar toggle button.

### 🔍 Integrated Search & Replace
- **Non-blocking Search Bar (`Ctrl + F`)**: Find occurrences with live match counting.
- **Full Replace (`Ctrl + H`)**: Single replace or "Replace All".
- **Advanced Match Options**: Toggle Case Sensitivity (`Aa`), Regular Expressions (`.*`), and Whole Word (`\b`).

### 🎨 Themes & Customization
- **Native Cinnamon Themes**: Switch between pre-installed GtkSource schemes:
  - `xed` (Linux Mint native look)
  - `solarized-dark` & `solarized-light` (Designed to reduce eye strain)
  - `oblivion` & `cobalt` (High-contrast dark modes)
  - `classic` & `tango` (Crisp light modes)
- **Font Selector**: Pick any installed monospace font (e.g. *DejaVu Sans Mono*, *Liberation Mono*, *Fira Code*, *JetBrains Mono*).
- **Word Wrap**: Toggleable word wrap mode (`Menu → Word Wrap`).

### 📊 Real-Time Status Bar
- Cursor Position: `Ln X, Col Y`
- Document Metrics: `X lines, Y words, Z chars`
- Retina Zoom Level: `Retina: 100%`
- Character Encoding: `UTF-8`

---

## 🚀 Getting Started

### 1. Launch Directly
To launch RetinaPad immediately from the terminal:
```bash
cd /home/bluechile/.gemini/antigravity/scratch/retina-notepad
./run.sh
```

Or open a specific file:
```bash
./run.sh /path/to/document.txt
```

### 2. Install to Linux Mint Cinnamon Menu
To add RetinaPad to your Cinnamon application menu (*Mint Menu → Accessories → RetinaPad*):
```bash
cd /home/bluechile/.gemini/antigravity/scratch/retina-notepad
./install.sh
```

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
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

## 🖥️ Linux Mint HiDPI Display Settings Tip

For high-resolution monitors on Linux Mint Cinnamon:
1. Open **System Settings → General**.
2. Under **Desktop Scaling**, select **Auto** or **Double (HiDPI)**.
3. In RetinaPad, you can use `Ctrl + Mouse Wheel` or the zoom buttons on the HeaderBar to adjust text readability without blurring.
