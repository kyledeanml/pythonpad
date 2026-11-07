#!/usr/bin/env python3
"""
RetinaPad - Editor Component
Provides a high-DPI (Retina) optimized text view using GtkSourceView 4.
"""

import os
import re
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GtkSource', '4')
gi.require_version('Pango', '1.0')

from gi.repository import Gtk, Gdk, GtkSource, Pango, GObject


# Ensure styles directory is in GtkSource StyleSchemeManager path
_styles_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles")
if os.path.exists(_styles_dir):
    GtkSource.StyleSchemeManager.get_default().prepend_search_path(_styles_dir)


class RetinaEditor(Gtk.ScrolledWindow):
    """
    Retina-optimized text editor widget with line numbers,
    crisp dynamic font scaling (Retina Vision), and full source view capabilities.
    """

    __gsignals__ = {
        'cursor-moved': (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        'content-modified': (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
        'zoom-changed': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'file-saved': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    ZOOM_STEPS = [
        0.50, 0.60, 0.70, 0.80, 0.90,
        1.00,
        1.10, 1.25, 1.40, 1.55, 1.75, 2.00, 2.25, 2.50, 3.00
    ]
    DEFAULT_ZOOM_INDEX = 5  # 1.00 (100%)

    def __init__(self, file_path=None):
        super().__init__()
        self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.set_shadow_type(Gtk.ShadowType.NONE)

        # File state
        self.file_path = None
        self.file_encoding = "UTF-8"
        self._is_modified = False

        # Font & Retina scaling
        self.base_font_family = "Monospace"
        self.base_font_size = 11
        self.zoom_index = self.DEFAULT_ZOOM_INDEX

        # GtkSource setup
        self.source_buffer = GtkSource.Buffer()
        self.source_view = GtkSource.View.new_with_buffer(self.source_buffer)
        self.add(self.source_view)

        # Editor configuration
        self._setup_view_properties()
        self._setup_retina_styles()
        self._setup_signals()

        # Apply default font & theme
        self.apply_retina_font()
        self.set_theme("pythonpad-neon")  # Dark mode with white and neon blue hue

        if file_path:
            self.load_file(file_path)

    def _setup_view_properties(self):
        """Configure editor view properties: line numbers, wrapping, spacing."""
        view = self.source_view
        view.set_show_line_numbers(True)
        view.set_highlight_current_line(True)
        view.set_show_line_marks(False)
        view.set_auto_indent(True)
        view.set_indent_on_tab(True)
        view.set_tab_width(4)
        view.set_insert_spaces_instead_of_tabs(True)
        view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        view.set_monospace(True)
        view.set_smart_home_end(GtkSource.SmartHomeEndType.ALWAYS)
        view.set_left_margin(12)
        view.set_right_margin(12)
        view.set_top_margin(10)
        view.set_bottom_margin(10)

    def _setup_retina_styles(self):
        """Apply CSS rules for crisp borders, clear gutters, and retina subpixel sharpness."""
        css_provider = Gtk.CssProvider()
        css = b"""
        textview {
            font-feature-settings: "liga 1, calt 1";
            background-color: #0a0e1a;
            color: #ffffff;
        }
        textview text {
            background-color: #0a0e1a;
            color: #ffffff;
        }
        textview border {
            background-color: #070a14;
            border-right: 1px solid rgba(0, 240, 255, 0.25);
            padding-right: 8px;
            padding-left: 6px;
        }
        """
        try:
            css_provider.load_from_data(css)
            context = self.source_view.get_style_context()
            context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        except Exception as e:
            print(f"Notice: Failed to load retina CSS: {e}")

    def _setup_signals(self):
        """Connect buffer and view signals."""
        self.source_buffer.connect("changed", self._on_buffer_changed)
        self.source_buffer.connect("notify::cursor-position", self._on_cursor_moved)

        # Ctrl + Mouse Wheel for Retina Zoom
        self.source_view.connect("scroll-event", self._on_scroll_event)

    def _on_buffer_changed(self, buffer):
        """Track modification state."""
        if not self._is_modified:
            self._is_modified = True
            self.emit("content-modified", True)

    def _on_cursor_moved(self, buffer, pspec):
        """Notify listeners when cursor moves (Line / Col update)."""
        line, col = self.get_cursor_position()
        self.emit("cursor-moved", line, col)

    def _on_scroll_event(self, widget, event):
        """Handle Ctrl + Mouse Wheel zoom in/out."""
        state = event.state & Gtk.accelerator_get_default_mod_mask()
        if state == Gdk.ModifierType.CONTROL_MASK:
            if event.direction == Gdk.ScrollDirection.UP:
                self.zoom_in()
                return True
            elif event.direction == Gdk.ScrollDirection.DOWN:
                self.zoom_out()
                return True
            elif event.direction == Gdk.ScrollDirection.SMOOTH:
                _, dy = event.get_scroll_deltas()
                if dy < 0:
                    self.zoom_in()
                    return True
                elif dy > 0:
                    self.zoom_out()
                    return True
        return False

    # --------------------------------------------------------------------------
    # Retina Vision & Font Scaling Engine
    # --------------------------------------------------------------------------
    def get_zoom_percent(self):
        """Return current zoom as an integer percentage (e.g. 100, 125, etc.)."""
        return int(round(self.ZOOM_STEPS[self.zoom_index] * 100))

    def zoom_in(self):
        """Increase font size one step on the Retina scaling curve."""
        if self.zoom_index < len(self.ZOOM_STEPS) - 1:
            self.zoom_index += 1
            self.apply_retina_font()
            self.emit("zoom-changed", self.get_zoom_percent())

    def zoom_out(self):
        """Decrease font size one step on the Retina scaling curve."""
        if self.zoom_index > 0:
            self.zoom_index -= 1
            self.apply_retina_font()
            self.emit("zoom-changed", self.get_zoom_percent())

    def reset_zoom(self):
        """Reset font size to 100% standard DPI baseline."""
        if self.zoom_index != self.DEFAULT_ZOOM_INDEX:
            self.zoom_index = self.DEFAULT_ZOOM_INDEX
            self.apply_retina_font()
            self.emit("zoom-changed", self.get_zoom_percent())

    def apply_retina_font(self):
        """
        Calculates and applies the high-DPI font size with subpixel anti-aliasing
        to ensure sharp glyph rendering at any scale.
        """
        scale = self.ZOOM_STEPS[self.zoom_index]
        scaled_size = max(6, int(round(self.base_font_size * scale)))

        font_desc = Pango.FontDescription(f"{self.base_font_family} {scaled_size}")
        self.source_view.override_font(font_desc)

    def set_font_family_and_size(self, family, size):
        """Update base font family and size."""
        self.base_font_family = family
        self.base_font_size = size
        self.apply_retina_font()

    # --------------------------------------------------------------------------
    # Visual Themes & Syntax Highlighting
    # --------------------------------------------------------------------------
    def set_theme(self, scheme_id):
        """Apply a GtkSourceView style scheme."""
        manager = GtkSource.StyleSchemeManager.get_default()
        scheme = manager.get_scheme(scheme_id)
        if not scheme:
            # Fallback
            for fallback in ['pythonpad-neon', 'oblivion', 'cobalt', 'xed', 'classic']:
                scheme = manager.get_scheme(fallback)
                if scheme:
                    break
        if scheme:
            self.source_buffer.set_style_scheme(scheme)

    def set_syntax_from_filename(self, filename):
        """Detect language syntax highlighting based on file extension."""
        lm = GtkSource.LanguageManager.get_default()
        lang = lm.guess_language(filename, None)
        self.source_buffer.set_language(lang)

    # --------------------------------------------------------------------------
    # Line Numbers & Editor Settings
    # --------------------------------------------------------------------------
    def set_show_line_numbers(self, show: bool):
        """Toggle line numbers visibility."""
        self.source_view.set_show_line_numbers(show)

    def get_show_line_numbers(self) -> bool:
        """Check if line numbers are enabled."""
        return self.source_view.get_show_line_numbers()

    def set_word_wrap(self, wrap: bool):
        """Toggle word wrapping."""
        mode = Gtk.WrapMode.WORD_CHAR if wrap else Gtk.WrapMode.NONE
        self.source_view.set_wrap_mode(mode)

    def get_word_wrap(self) -> bool:
        """Check if word wrapping is enabled."""
        return self.source_view.get_wrap_mode() != Gtk.WrapMode.NONE

    def set_highlight_current_line(self, highlight: bool):
        """Toggle highlighting of the active cursor line."""
        self.source_view.set_highlight_current_line(highlight)

    def goto_line(self, line_number: int):
        """Jump cursor to a specific 1-based line number."""
        self.goto_line_col(line_number, 1)

    def goto_line_col(self, line_number: int, column: int = 1):
        """Jump cursor to a specific 1-based line and column, and scroll to view."""
        buf = self.source_buffer
        total_lines = buf.get_line_count()
        target_line = max(0, min(line_number - 1, total_lines - 1))

        iter_at_line = buf.get_iter_at_line(target_line)
        line_length = iter_at_line.get_chars_in_line()
        offset = max(0, min(column - 1, max(0, line_length - 1)))
        iter_at_line.forward_chars(offset)

        buf.place_cursor(iter_at_line)
        self.source_view.scroll_to_iter(iter_at_line, 0.25, False, 0.0, 0.0)
        self.source_view.grab_focus()

    # --------------------------------------------------------------------------
    # Advanced Code Editing Operations
    # --------------------------------------------------------------------------
    def toggle_comment(self):
        """Toggle '#' comment on current line or selected block."""
        buf = self.source_buffer
        buf.begin_user_action()
        try:
            bounds = buf.get_selection_bounds()
            if bounds:
                start, end = bounds
                start_l = start.get_line()
                end_l = end.get_line()
                if end.get_line_offset() == 0 and end_l > start_l:
                    end_l -= 1
            else:
                cur = buf.get_iter_at_mark(buf.get_insert())
                start_l = end_l = cur.get_line()

            # Determine whether all selected lines are commented
            all_commented = True
            lines_iters = []
            for l in range(start_l, end_l + 1):
                it = buf.get_iter_at_line(l)
                eol = it.copy()
                eol.forward_to_line_end()
                line_str = buf.get_text(it, eol, True).strip()
                if line_str and not line_str.startswith("#"):
                    all_commented = False
                lines_iters.append(l)

            # Apply comment or uncomment
            for l in lines_iters:
                it = buf.get_iter_at_line(l)
                eol = it.copy()
                eol.forward_to_line_end()
                line_str = buf.get_text(it, eol, True)

                if all_commented:
                    # Remove comment
                    if "# " in line_str:
                        new_line = line_str.replace("# ", "", 1)
                    elif "#" in line_str:
                        new_line = line_str.replace("#", "", 1)
                    else:
                        new_line = line_str
                    buf.delete(it, eol)
                    it = buf.get_iter_at_line(l)
                    buf.insert(it, new_line)
                else:
                    # Add comment
                    buf.insert(it, "# ")
        finally:
            buf.end_user_action()

    def duplicate_line(self):
        """Duplicate current line or selected text (Ctrl+D)."""
        buf = self.source_buffer
        buf.begin_user_action()
        try:
            bounds = buf.get_selection_bounds()
            if bounds:
                start, end = bounds
                text = buf.get_text(start, end, True)
                buf.insert(end, text)
            else:
                cur = buf.get_iter_at_mark(buf.get_insert())
                l = cur.get_line()
                it = buf.get_iter_at_line(l)
                eol = it.copy()
                eol.forward_to_line_end()
                line_text = buf.get_text(it, eol, True)
                buf.insert(eol, "\n" + line_text)
        finally:
            buf.end_user_action()

    def delete_line(self):
        """Delete entire current line (Ctrl+Shift+K)."""
        buf = self.source_buffer
        buf.begin_user_action()
        try:
            cur = buf.get_iter_at_mark(buf.get_insert())
            l = cur.get_line()
            it = buf.get_iter_at_line(l)
            eol = it.copy()
            if not eol.forward_line():
                eol.forward_to_line_end()
            buf.delete(it, eol)
        finally:
            buf.end_user_action()

    def move_line_up(self):
        """Move active line up by one line (Alt+Up)."""
        buf = self.source_buffer
        cur = buf.get_iter_at_mark(buf.get_insert())
        l = cur.get_line()
        if l == 0:
            return
        buf.begin_user_action()
        try:
            it = buf.get_iter_at_line(l)
            eol = it.copy()
            eol.forward_to_line_end()
            cur_line = buf.get_text(it, eol, True)

            prev_it = buf.get_iter_at_line(l - 1)
            prev_eol = prev_it.copy()
            prev_eol.forward_to_line_end()
            prev_line = buf.get_text(prev_it, prev_eol, True)

            # Swap lines
            buf.delete(it, eol)
            it = buf.get_iter_at_line(l)
            buf.insert(it, prev_line)

            prev_it = buf.get_iter_at_line(l - 1)
            prev_eol = prev_it.copy()
            prev_eol.forward_to_line_end()
            buf.delete(prev_it, prev_eol)
            prev_it = buf.get_iter_at_line(l - 1)
            buf.insert(prev_it, cur_line)

            self.goto_line(l)
        finally:
            buf.end_user_action()

    def move_line_down(self):
        """Move active line down by one line (Alt+Down)."""
        buf = self.source_buffer
        cur = buf.get_iter_at_mark(buf.get_insert())
        l = cur.get_line()
        if l >= buf.get_line_count() - 1:
            return
        buf.begin_user_action()
        try:
            it = buf.get_iter_at_line(l)
            eol = it.copy()
            eol.forward_to_line_end()
            cur_line = buf.get_text(it, eol, True)

            next_it = buf.get_iter_at_line(l + 1)
            next_eol = next_it.copy()
            next_eol.forward_to_line_end()
            next_line = buf.get_text(next_it, next_eol, True)

            buf.delete(next_it, next_eol)
            next_it = buf.get_iter_at_line(l + 1)
            buf.insert(next_it, cur_line)

            it = buf.get_iter_at_line(l)
            eol = it.copy()
            eol.forward_to_line_end()
            buf.delete(it, eol)
            it = buf.get_iter_at_line(l)
            buf.insert(it, next_line)

            self.goto_line(l + 2)
        finally:
            buf.end_user_action()

    def join_lines(self):
        """Join current line with the next line (Ctrl+J)."""
        buf = self.source_buffer
        cur = buf.get_iter_at_mark(buf.get_insert())
        l = cur.get_line()
        if l >= buf.get_line_count() - 1:
            return
        buf.begin_user_action()
        try:
            it = buf.get_iter_at_line(l)
            it.forward_to_line_end()
            next_it = buf.get_iter_at_line(l + 1)
            # Find first non-whitespace on next line
            while not next_it.ends_line() and next_it.get_char() in (' ', '\t'):
                next_it.forward_char()
            buf.delete(it, next_it)
            buf.insert(it, " ")
        finally:
            buf.end_user_action()

    def convert_case(self, upper: bool = True):
        """Convert selected text to UPPERCASE or lowercase (Ctrl+Shift+U / Ctrl+U)."""
        buf = self.source_buffer
        bounds = buf.get_selection_bounds()
        if not bounds:
            return
        buf.begin_user_action()
        try:
            start, end = bounds
            text = buf.get_text(start, end, True)
            new_text = text.upper() if upper else text.lower()
            buf.delete(start, end)
            buf.insert_at_cursor(new_text)
        finally:
            buf.end_user_action()

    def indent_block(self, forward: bool = True):
        """Indent or unindent current line or selected block by 4 spaces."""
        buf = self.source_buffer
        buf.begin_user_action()
        try:
            bounds = buf.get_selection_bounds()
            if bounds:
                start, end = bounds
                start_l = start.get_line()
                end_l = end.get_line()
                if end.get_line_offset() == 0 and end_l > start_l:
                    end_l -= 1
            else:
                cur = buf.get_iter_at_mark(buf.get_insert())
                start_l = end_l = cur.get_line()

            for l in range(start_l, end_l + 1):
                it = buf.get_iter_at_line(l)
                if forward:
                    buf.insert(it, "    ")
                else:
                    eol = it.copy()
                    eol.forward_to_line_end()
                    line_str = buf.get_text(it, eol, True)
                    if line_str.startswith("    "):
                        del_end = it.copy()
                        del_end.forward_chars(4)
                        buf.delete(it, del_end)
                    elif line_str.startswith("\t"):
                        del_end = it.copy()
                        del_end.forward_chars(1)
                        buf.delete(it, del_end)
                    else:
                        spaces = len(line_str) - len(line_str.lstrip(" "))
                        if spaces > 0:
                            del_end = it.copy()
                            del_end.forward_chars(spaces)
                            buf.delete(it, del_end)
        finally:
            buf.end_user_action()

    # --------------------------------------------------------------------------
    # Document Stats
    # --------------------------------------------------------------------------
    def get_cursor_position(self):
        """Return (line, column) tuple (1-based line, 1-based column)."""
        buf = self.source_buffer
        insert_mark = buf.get_insert()
        cursor_iter = buf.get_iter_at_mark(insert_mark)
        line = cursor_iter.get_line() + 1
        col = cursor_iter.get_line_offset() + 1
        return line, col

    def get_document_statistics(self):
        """Return dict with total lines, words, characters, line, col."""
        buf = self.source_buffer
        start, end = buf.get_bounds()
        text = buf.get_text(start, end, True)

        total_lines = buf.get_line_count()
        char_count = len(text)
        word_count = len(re.findall(r'\S+', text))
        line, col = self.get_cursor_position()

        return {
            'line': line,
            'col': col,
            'total_lines': total_lines,
            'word_count': word_count,
            'char_count': char_count,
        }

    # --------------------------------------------------------------------------
    # File Operations
    # --------------------------------------------------------------------------
    def is_modified(self) -> bool:
        return self._is_modified

    def get_text(self) -> str:
        buf = self.source_buffer
        start, end = buf.get_bounds()
        return buf.get_text(start, end, True)

    def set_text(self, text: str):
        self.source_buffer.set_text(text)
        self._is_modified = False
        self.emit("content-modified", False)

    def load_file(self, path: str) -> bool:
        """Load text from file path with automatic encoding fallback."""
        try:
            with open(path, 'rb') as f:
                raw_bytes = f.read()

            for enc in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    text = raw_bytes.decode(enc)
                    self.file_encoding = enc.upper()
                    break
                except UnicodeDecodeError:
                    continue
            else:
                text = raw_bytes.decode('utf-8', errors='replace')
                self.file_encoding = 'UTF-8 (lossy)'

            self.file_path = os.path.abspath(path)
            self.set_text(text)
            self.set_syntax_from_filename(self.file_path)
            self._is_modified = False
            self.emit("content-modified", False)
            return True
        except Exception as e:
            print(f"Error loading file {path}: {e}")
            raise e

    def save_file(self, path: str = None) -> bool:
        """Save buffer content to disk."""
        target_path = path or self.file_path
        if not target_path:
            raise ValueError("No file path specified to save.")

        text = self.get_text()
        encoding = 'utf-8' if 'lossy' in self.file_encoding.lower() else self.file_encoding.lower()

        with open(target_path, 'w', encoding=encoding) as f:
            f.write(text)

        self.file_path = os.path.abspath(target_path)
        self._is_modified = False
        self.set_syntax_from_filename(self.file_path)
        self.emit("content-modified", False)
        self.emit("file-saved", self.file_path)
        return True
