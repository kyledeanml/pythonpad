#!/usr/bin/env python3
"""
PythonPad - Editor Component
Provides a high-DPI (Retina) optimized text view using GtkSourceView 4.
"""

import os
import re
import tempfile
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
gi.require_version('GtkSource', '4')
gi.require_version('Pango', '1.0')

from gi.repository import Gtk, Gdk, GdkPixbuf, GtkSource, Pango, GObject
import cairo


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
    _shared_css_provider = None
    _watermark_pixbuf = None
    _watermark_loaded = False

    def __init__(self, file_path=None):
        super().__init__()
        self.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.set_shadow_type(Gtk.ShadowType.NONE)

        # File state
        self.file_path = None
        self.file_encoding = "UTF-8"
        self.line_ending = "LF"
        self._is_modified = False

        # Cached statistics for O(1) lookups when buffer hasn't changed
        self._stats_dirty = True
        self._cached_word_count = 0

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
            expanded = os.path.abspath(os.path.expanduser(file_path))
            if os.path.isfile(expanded):
                self.load_file(expanded)
            elif not os.path.exists(expanded):
                # New file path passed via CLI: bind path and syntax without crashing
                self.file_path = expanded
                self.set_syntax_from_filename(self.file_path)

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
        if RetinaEditor._shared_css_provider is None:
            provider = Gtk.CssProvider()
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
                provider.load_from_data(css)
                RetinaEditor._shared_css_provider = provider
            except Exception as e:
                print(f"Notice: Failed to load retina CSS: {e}")
                return

        context = self.source_view.get_style_context()
        context.add_provider(
            RetinaEditor._shared_css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _setup_signals(self):
        """Connect buffer and view signals."""
        self.source_buffer.connect("changed", self._on_buffer_changed)
        self.source_buffer.connect("notify::cursor-position", self._on_cursor_moved)

        # Ctrl + Mouse Wheel for Retina Zoom
        self.source_view.connect("scroll-event", self._on_scroll_event)

        # Translucent Python-on-Yoga-Pad background watermark
        self.source_view.connect_after("draw", self._on_draw_watermark)

    @classmethod
    def _get_watermark_pixbuf(cls):
        """Load and cache the official PythonPad SVG (Python logo on yoga pad) for the editor background."""
        if not cls._watermark_loaded:
            cls._watermark_loaded = True
            svg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pythonpad.svg")
            if os.path.exists(svg_path):
                try:
                    cls._watermark_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        svg_path, 340, 340, True
                    )
                except Exception:
                    cls._watermark_pixbuf = None
        return cls._watermark_pixbuf

    def _on_draw_watermark(self, widget, cr):
        """Render the translucent darker-blue Python logo sitting on an unassuming yoga pad."""
        pixbuf = self._get_watermark_pixbuf()
        if pixbuf is None:
            return False

        try:
            text_win = widget.get_window(Gtk.TextWindowType.TEXT)
            alloc = widget.get_allocation()
            if text_win is not None:
                gutter_w = alloc.width - text_win.get_width()
                view_w = text_win.get_width()
                view_h = text_win.get_height()
            else:
                gutter_w = 48
                view_w = alloc.width - gutter_w
                view_h = alloc.height

            pw = pixbuf.get_width()
            ph = pixbuf.get_height()
            if view_w < 120 or view_h < 120:
                return False

            # Center the watermark in the lower-right / center-right of the editor canvas
            x = gutter_w + max(20, (view_w - pw) * 0.55)
            y = max(20, (view_h - ph) * 0.58)

            cr.save()
            cr.set_operator(cairo.OPERATOR_OVER)
            Gdk.cairo_set_source_pixbuf(cr, pixbuf, x, y)
            cr.paint_with_alpha(0.32)
            cr.restore()
        except Exception:
            pass
        return False

    def _on_buffer_changed(self, buffer):
        """Track modification state and mark document stats cache dirty."""
        self._stats_dirty = True
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
        self.base_font_size = max(6, int(size))
        self.apply_retina_font()

    # --------------------------------------------------------------------------
    # Visual Themes & Syntax Highlighting
    # --------------------------------------------------------------------------
    def set_theme(self, scheme_id):
        """Apply a GtkSourceView style scheme."""
        manager = GtkSource.StyleSchemeManager.get_default()
        scheme = manager.get_scheme(scheme_id)
        if not scheme:
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
        total_lines = max(1, buf.get_line_count())
        target_line = max(0, min(int(line_number) - 1, total_lines - 1))

        iter_at_line = buf.get_iter_at_line(target_line)
        eol = iter_at_line.copy()
        if not eol.ends_line():
            eol.forward_to_line_end()
        line_length = eol.get_line_offset()
        offset = max(0, min(int(column) - 1, line_length))
        iter_at_line.set_line_offset(offset)

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

            # Determine whether all non-empty selected lines are commented
            non_empty_count = 0
            all_commented = True
            lines_iters = list(range(start_l, end_l + 1))

            for l in lines_iters:
                it = buf.get_iter_at_line(l)
                eol = it.copy()
                if not eol.ends_line():
                    eol.forward_to_line_end()
                line_str = buf.get_text(it, eol, True).strip()
                if line_str:
                    non_empty_count += 1
                    if not line_str.startswith("#"):
                        all_commented = False

            if non_empty_count == 0:
                all_commented = False

            # Apply comment or uncomment
            for l in lines_iters:
                it = buf.get_iter_at_line(l)
                eol = it.copy()
                if not eol.ends_line():
                    eol.forward_to_line_end()
                line_str = buf.get_text(it, eol, True)

                if all_commented:
                    new_line = re.sub(r'^(\s*)# ?', r'\1', line_str, count=1)
                    if new_line != line_str:
                        buf.delete(it, eol)
                        it = buf.get_iter_at_line(l)
                        buf.insert(it, new_line)
                else:
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
                if not eol.ends_line():
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
                if not eol.ends_line():
                    eol.forward_to_line_end()
                if l > 0:
                    it.backward_char()
            buf.delete(it, eol)
        finally:
            buf.end_user_action()

    def move_line_up(self):
        """Move active line up by one line (Alt+Up)."""
        buf = self.source_buffer
        cur = buf.get_iter_at_mark(buf.get_insert())
        l = cur.get_line()
        col = cur.get_line_offset() + 1
        if l == 0:
            return
        buf.begin_user_action()
        try:
            it = buf.get_iter_at_line(l)
            eol = it.copy()
            if not eol.ends_line():
                eol.forward_to_line_end()
            cur_line = buf.get_text(it, eol, True)

            prev_it = buf.get_iter_at_line(l - 1)
            prev_eol = prev_it.copy()
            if not prev_eol.ends_line():
                prev_eol.forward_to_line_end()
            prev_line = buf.get_text(prev_it, prev_eol, True)

            buf.delete(it, eol)
            it = buf.get_iter_at_line(l)
            buf.insert(it, prev_line)

            prev_it = buf.get_iter_at_line(l - 1)
            prev_eol = prev_it.copy()
            if not prev_eol.ends_line():
                prev_eol.forward_to_line_end()
            buf.delete(prev_it, prev_eol)
            prev_it = buf.get_iter_at_line(l - 1)
            buf.insert(prev_it, cur_line)

            self.goto_line_col(l, col)
        finally:
            buf.end_user_action()

    def move_line_down(self):
        """Move active line down by one line (Alt+Down)."""
        buf = self.source_buffer
        cur = buf.get_iter_at_mark(buf.get_insert())
        l = cur.get_line()
        col = cur.get_line_offset() + 1
        if l >= buf.get_line_count() - 1:
            return
        buf.begin_user_action()
        try:
            it = buf.get_iter_at_line(l)
            eol = it.copy()
            if not eol.ends_line():
                eol.forward_to_line_end()
            cur_line = buf.get_text(it, eol, True)

            next_it = buf.get_iter_at_line(l + 1)
            next_eol = next_it.copy()
            if not next_eol.ends_line():
                next_eol.forward_to_line_end()
            next_line = buf.get_text(next_it, next_eol, True)

            buf.delete(next_it, next_eol)
            next_it = buf.get_iter_at_line(l + 1)
            buf.insert(next_it, cur_line)

            it = buf.get_iter_at_line(l)
            eol = it.copy()
            if not eol.ends_line():
                eol.forward_to_line_end()
            buf.delete(it, eol)
            it = buf.get_iter_at_line(l)
            buf.insert(it, next_line)

            self.goto_line_col(l + 2, col)
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
            if not it.ends_line():
                it.forward_to_line_end()
            next_it = buf.get_iter_at_line(l + 1)
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
            start_offset = start.get_offset()
            text = buf.get_text(start, end, True)
            new_text = text.upper() if upper else text.lower()
            buf.delete(start, end)
            ins_iter = buf.get_iter_at_offset(start_offset)
            buf.insert(ins_iter, new_text)
            sel_start = buf.get_iter_at_offset(start_offset)
            sel_end = buf.get_iter_at_offset(start_offset + len(new_text))
            buf.select_range(sel_start, sel_end)
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
                    if not eol.ends_line():
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
    # Document Stats (Optimized with O(1) GTK B-Tree counts & dirty-flag cache)
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
        total_lines = buf.get_line_count()
        char_count = buf.get_char_count()
        line, col = self.get_cursor_position()

        if self._stats_dirty:
            if char_count <= 2_000_000:
                start, end = buf.get_bounds()
                text = buf.get_text(start, end, True)
                self._cached_word_count = len(text.split())
            self._stats_dirty = False

        return {
            'line': line,
            'col': col,
            'total_lines': total_lines,
            'word_count': self._cached_word_count,
            'char_count': char_count,
        }

    # --------------------------------------------------------------------------
    # File Operations (Null-Byte Safe & Atomic Write)
    # --------------------------------------------------------------------------
    def is_modified(self) -> bool:
        return self._is_modified

    def get_text(self) -> str:
        buf = self.source_buffer
        start, end = buf.get_bounds()
        return buf.get_text(start, end, True)

    def set_text(self, text: str, undoable: bool = False):
        clean_text = (text or "").replace("\x00", "\ufffd")
        buf = self.source_buffer
        if not undoable:
            buf.begin_not_undoable_action()
        try:
            buf.set_text(clean_text)
        finally:
            if not undoable:
                buf.end_not_undoable_action()
        self._is_modified = False
        self._stats_dirty = True
        self.emit("content-modified", False)

    def load_file(self, path: str) -> bool:
        """Load text from file path with automatic encoding fallback and null-byte protection."""
        try:
            with open(path, 'rb') as f:
                raw_bytes = f.read()

            had_nulls = b'\x00' in raw_bytes
            if had_nulls:
                raw_bytes = raw_bytes.replace(b'\x00', b'\xef\xbf\xbd')

            for enc in ('utf-8', 'latin-1', 'cp1252'):
                try:
                    text = raw_bytes.decode(enc)
                    self.file_encoding = enc.upper()
                    break
                except UnicodeDecodeError:
                    continue
            else:
                text = raw_bytes.decode('utf-8', errors='replace')
                self.file_encoding = 'UTF-8 (lossy)'

            if had_nulls and 'lossy' not in self.file_encoding.lower():
                self.file_encoding = f"{self.file_encoding} (binary)"

            self.line_ending = "CRLF" if "\r\n" in text else "LF"
            if self.line_ending == "CRLF":
                text = text.replace("\r\n", "\n")

            self.file_path = os.path.abspath(path)
            self.set_text(text, undoable=False)
            self.set_syntax_from_filename(self.file_path)
            self._is_modified = False
            self.emit("content-modified", False)
            return True
        except Exception as e:
            print(f"Error loading file {path}: {e}")
            raise e

    def save_file(self, path: str = None) -> bool:
        """Save buffer content to disk safely without risking zero-byte truncation on encoding error."""
        target_path = path or self.file_path
        if not target_path:
            raise ValueError("No file path specified to save.")

        abs_target = os.path.abspath(target_path)
        text = self.get_text()
        if self.line_ending == "CRLF":
            text_to_write = text.replace("\n", "\r\n")
        else:
            text_to_write = text

        enc_raw = self.file_encoding.split()[0].lower()
        encoding = 'utf-8' if enc_raw not in ('utf-8', 'latin-1', 'cp1252') else enc_raw

        # Encode in memory BEFORE touching disk so UnicodeEncodeError never truncates the file
        try:
            encoded_bytes = text_to_write.encode(encoding)
        except UnicodeEncodeError:
            encoding = 'utf-8'
            self.file_encoding = 'UTF-8'
            encoded_bytes = text_to_write.encode('utf-8')

        # Preserve permissions and write safely
        target_dir = os.path.dirname(abs_target) or "."
        existing_mode = None
        is_symlink = os.path.islink(abs_target)
        if os.path.exists(abs_target):
            try:
                existing_mode = os.stat(abs_target).st_mode
            except OSError:
                pass

        if not is_symlink and os.access(target_dir, os.W_OK):
            fd, tmp_path = tempfile.mkstemp(prefix=".pythonpad_save_", dir=target_dir)
            try:
                with os.fdopen(fd, 'wb') as f:
                    f.write(encoded_bytes)
                    f.flush()
                    os.fsync(f.fileno())
                if existing_mode is not None:
                    try:
                        os.chmod(tmp_path, existing_mode)
                    except OSError:
                        pass
                os.replace(tmp_path, abs_target)
            except Exception:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
                raise
        else:
            with open(abs_target, 'wb') as f:
                f.write(encoded_bytes)

        self.file_path = abs_target
        self._is_modified = False
        self.set_syntax_from_filename(self.file_path)
        self.emit("content-modified", False)
        self.emit("file-saved", self.file_path)
        return True
