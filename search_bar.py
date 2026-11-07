#!/usr/bin/env python3
"""
PythonPad - Search & Replace Component
Provides an integrated search and replace overlay/bar with GtkSource.SearchContext.
Supports dynamic editor attachment across multiple document tabs.
"""

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GtkSource', '4')

from gi.repository import Gtk, Gdk, GtkSource, GObject


class SearchBar(Gtk.Revealer):
    """
    Search and Replace toolbar that reveals/hides smoothly and connects to the active RetinaEditor.
    """

    __gsignals__ = {
        'closed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, editor=None):
        super().__init__()
        self.editor = None
        self.search_context = None
        self._occ_handler_id = None
        self.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.set_transition_duration(150)

        # GtkSource search objects
        self.search_settings = GtkSource.SearchSettings()
        self.search_settings.set_wrap_around(True)

        # UI Container
        self._build_ui()
        self._setup_events()

        if editor:
            self.set_editor(editor)

    def set_editor(self, editor):
        """Attach search bar to an active editor instance cleanly."""
        if self.editor is editor and self.search_context is not None:
            self.search_context.set_highlight(self.get_reveal_child())
            self.update_match_count()
            return

        if self.search_context is not None:
            if self._occ_handler_id is not None:
                try:
                    self.search_context.disconnect(self._occ_handler_id)
                except Exception:
                    pass
                self._occ_handler_id = None
            try:
                self.search_context.set_highlight(False)
            except Exception:
                pass

        self.editor = editor
        if self.editor and hasattr(self.editor, 'source_buffer'):
            self.search_context = GtkSource.SearchContext.new(
                self.editor.source_buffer,
                self.search_settings
            )
            self.search_context.set_highlight(self.get_reveal_child())
            self._occ_handler_id = self.search_context.connect(
                "notify::occurrences-count",
                lambda ctx, pspec: self.update_match_count()
            )
            self.update_match_count()
        else:
            self.search_context = None
            self.lbl_status.set_text("")

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        main_box.get_style_context().add_class("search-bar")
        main_box.set_margin_start(10)
        main_box.set_margin_end(10)
        main_box.set_margin_top(6)
        main_box.set_margin_bottom(6)

        # --- Row 1: Find Row ---
        find_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        find_lbl = Gtk.Label(label="Find:")
        find_lbl.set_size_request(60, -1)
        find_lbl.set_xalign(0)
        find_box.pack_start(find_lbl, False, False, 0)

        self.find_entry = Gtk.SearchEntry()
        self.find_entry.set_placeholder_text("Search text...")
        self.find_entry.set_width_chars(25)
        find_box.pack_start(self.find_entry, True, True, 0)

        # Nav buttons
        self.btn_prev = Gtk.Button.new_from_icon_name("go-up-symbolic", Gtk.IconSize.BUTTON)
        self.btn_prev.set_tooltip_text("Previous match (Shift+Enter)")
        find_box.pack_start(self.btn_prev, False, False, 0)

        self.btn_next = Gtk.Button.new_from_icon_name("go-down-symbolic", Gtk.IconSize.BUTTON)
        self.btn_next.set_tooltip_text("Next match (Enter)")
        find_box.pack_start(self.btn_next, False, False, 0)

        # Options
        self.btn_case = Gtk.ToggleButton(label="Aa")
        self.btn_case.set_tooltip_text("Match Case")
        find_box.pack_start(self.btn_case, False, False, 0)

        self.btn_regex = Gtk.ToggleButton(label=".*")
        self.btn_regex.set_tooltip_text("Regular Expression")
        find_box.pack_start(self.btn_regex, False, False, 0)

        self.btn_word = Gtk.ToggleButton(label="\\b")
        self.btn_word.set_tooltip_text("Whole Word Only")
        find_box.pack_start(self.btn_word, False, False, 0)

        self.lbl_status = Gtk.Label(label="")
        self.lbl_status.set_xalign(0)
        self.lbl_status.set_margin_start(6)
        find_box.pack_start(self.lbl_status, False, False, 0)

        self.btn_close = Gtk.Button.new_from_icon_name("window-close-symbolic", Gtk.IconSize.BUTTON)
        self.btn_close.set_relief(Gtk.ReliefStyle.NONE)
        self.btn_close.set_tooltip_text("Close Search (Escape)")
        find_box.pack_start(self.btn_close, False, False, 0)

        main_box.pack_start(find_box, False, False, 0)

        # --- Row 2: Replace Row ---
        self.replace_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        replace_lbl = Gtk.Label(label="Replace:")
        replace_lbl.set_size_request(60, -1)
        replace_lbl.set_xalign(0)
        self.replace_box.pack_start(replace_lbl, False, False, 0)

        self.replace_entry = Gtk.Entry()
        self.replace_entry.set_placeholder_text("Replace with...")
        self.replace_box.pack_start(self.replace_entry, True, True, 0)

        self.btn_replace = Gtk.Button(label="Replace")
        self.btn_replace.set_tooltip_text("Replace current match")
        self.replace_box.pack_start(self.btn_replace, False, False, 0)

        self.btn_replace_all = Gtk.Button(label="Replace All")
        self.btn_replace_all.set_tooltip_text("Replace all occurrences")
        self.replace_box.pack_start(self.btn_replace_all, False, False, 0)

        dummy = Gtk.Box()
        dummy.set_size_request(30, -1)
        self.replace_box.pack_start(dummy, False, False, 0)

        main_box.pack_start(self.replace_box, False, False, 0)

        # Outer frame
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.OUT)
        frame.add(main_box)

        self.add(frame)

    def _setup_events(self):
        self.find_entry.connect("search-changed", self._on_search_changed)
        self.find_entry.connect("activate", lambda w: self.find_next(advance=True))
        self.find_entry.connect("key-press-event", self._on_key_press)
        self.replace_entry.connect("activate", lambda w: self.replace_current())
        self.replace_entry.connect("key-press-event", self._on_key_press)

        self.btn_prev.connect("clicked", lambda w: self.find_previous())
        self.btn_next.connect("clicked", lambda w: self.find_next(advance=True))
        self.btn_case.connect("toggled", self._on_option_toggled)
        self.btn_regex.connect("toggled", self._on_option_toggled)
        self.btn_word.connect("toggled", self._on_option_toggled)
        self.btn_replace.connect("clicked", lambda w: self.replace_current())
        self.btn_replace_all.connect("clicked", lambda w: self.replace_all())
        self.btn_close.connect("clicked", lambda w: self.close())

    def _on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.close()
            return True
        elif event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            if event.state & Gdk.ModifierType.SHIFT_MASK:
                self.find_previous()
                return True
        return False

    def _on_search_changed(self, entry):
        text = entry.get_text()
        self.search_settings.set_search_text(text if text else None)
        self.update_match_count()
        if text:
            self.find_next(advance=False)

    def _on_option_toggled(self, button):
        self.search_settings.set_case_sensitive(self.btn_case.get_active())
        self.search_settings.set_regex_enabled(self.btn_regex.get_active())
        self.search_settings.set_at_word_boundaries(self.btn_word.get_active())
        self.update_match_count()

    def update_match_count(self):
        query = self.find_entry.get_text()
        if not query or not self.search_context:
            self.lbl_status.set_text("")
            return

        regex_err = self.search_context.get_regex_error()
        if regex_err is not None:
            self.lbl_status.set_text("Invalid regex")
            return

        count = self.search_context.get_occurrences_count()
        if count == -1:
            self.lbl_status.set_text("Searching...")
        elif count == 0:
            self.lbl_status.set_text("No matches")
        elif count == 1:
            self.lbl_status.set_text("1 match")
        else:
            self.lbl_status.set_text(f"{count} matches")

    def find_next(self, advance=True):
        if not self.find_entry.get_text() or not self.editor or not self.search_context:
            return

        buf = self.editor.source_buffer
        selection = buf.get_selection_bounds()
        if selection:
            start_iter = selection[1] if advance else selection[0]
        else:
            insert_mark = buf.get_insert()
            start_iter = buf.get_iter_at_mark(insert_mark)

        res, match_start, match_end, _wrapped = self.search_context.forward(start_iter)
        if res:
            buf.select_range(match_start, match_end)
            self.editor.source_view.scroll_to_iter(match_start, 0.2, False, 0.0, 0.0)
            self.update_match_count()
        else:
            self.lbl_status.set_text("No matches")

    def find_previous(self):
        if not self.find_entry.get_text() or not self.editor or not self.search_context:
            return

        buf = self.editor.source_buffer
        selection = buf.get_selection_bounds()
        if selection:
            start_iter = selection[0]
        else:
            insert_mark = buf.get_insert()
            start_iter = buf.get_iter_at_mark(insert_mark)

        res, match_start, match_end, _wrapped = self.search_context.backward(start_iter)
        if res:
            buf.select_range(match_start, match_end)
            self.editor.source_view.scroll_to_iter(match_start, 0.2, False, 0.0, 0.0)
            self.update_match_count()
        else:
            self.lbl_status.set_text("No matches")

    def replace_current(self):
        if not self.editor or not self.search_context:
            return
        replacement = self.replace_entry.get_text()
        buf = self.editor.source_buffer
        bounds = buf.get_selection_bounds()
        if bounds:
            start, end = bounds
            buf.begin_user_action()
            try:
                self.search_context.replace(start, end, replacement, -1)
            except Exception as e:
                self.lbl_status.set_text(f"Error: {e}")
            finally:
                buf.end_user_action()
            self.find_next(advance=True)
        else:
            self.find_next(advance=True)

    def replace_all(self):
        if not self.editor or not self.search_context:
            return
        replacement = self.replace_entry.get_text()
        buf = self.editor.source_buffer
        buf.begin_user_action()
        try:
            count = self.search_context.replace_all(replacement, -1)
            self.lbl_status.set_text(f"Replaced {count} occurrences")
        except Exception as e:
            self.lbl_status.set_text(f"Error: {e}")
        finally:
            buf.end_user_action()

    def _populate_from_selection(self):
        if self.editor:
            bounds = self.editor.source_buffer.get_selection_bounds()
            if bounds:
                sel_text = self.editor.source_buffer.get_text(bounds[0], bounds[1], True)
                if sel_text and "\n" not in sel_text:
                    self.find_entry.set_text(sel_text)
                    self.find_entry.select_region(0, -1)

    def show_find(self):
        self.replace_box.set_visible(False)
        self.set_reveal_child(True)
        if self.search_context:
            self.search_context.set_highlight(True)
        self._populate_from_selection()
        self.find_entry.grab_focus()
        self.update_match_count()

    def show_replace(self):
        self.replace_box.set_visible(True)
        self.set_reveal_child(True)
        if self.search_context:
            self.search_context.set_highlight(True)
        self._populate_from_selection()
        self.find_entry.grab_focus()
        self.update_match_count()

    def close(self):
        self.set_reveal_child(False)
        if self.search_context:
            self.search_context.set_highlight(False)
        if self.editor and hasattr(self.editor, 'source_view'):
            self.editor.source_view.grab_focus()
        self.emit("closed")
