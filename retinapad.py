#!/usr/bin/env python3
"""
RetinaPad - Simple Notepad with Retina Vision and Line Numbers
Designed specifically for Linux Mint Cinnamon.
"""

import sys
import os
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
gi.require_version('GtkSource', '4')
gi.require_version('Pango', '1.0')

from gi.repository import Gtk, Gdk, GdkPixbuf, GtkSource, Pango, GLib, Gio
from editor import RetinaEditor
from search_bar import SearchBar


class RetinaPadWindow(Gtk.ApplicationWindow):
    """Main application window for RetinaPad."""

    APP_NAME = "RetinaPad"
    APP_VERSION = "1.0"

    def __init__(self, app, file_path=None):
        super().__init__(application=app, title=self.APP_NAME)
        self.set_default_size(950, 650)
        self.set_position(Gtk.WindowPosition.CENTER)

        # Set window icon if available
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "retinapad.svg")
        if os.path.exists(icon_path):
            self.set_icon_from_file(icon_path)

        # Active file tracker
        self.current_filename = "Untitled Document"

        # Construct UI
        self._build_header_bar()
        self._build_editor_area()
        self._build_status_bar()
        self._setup_shortcuts()

        # Connect delete/close event
        self.connect("delete-event", self._on_delete_event)

        # Open file if passed via CLI
        if file_path:
            self.open_path(file_path)
        else:
            self.update_title()

        self.show_all()
        # Search bar is initially hidden
        self.search_bar.set_reveal_child(False)

    def _build_header_bar(self):
        """Header bar matching modern Linux Mint / Cinnamon style."""
        self.header = Gtk.HeaderBar()
        self.header.set_show_close_button(True)
        self.header.set_title(self.APP_NAME)
        self.header.set_subtitle(self.current_filename)
        self.set_titlebar(self.header)

        # Left controls: New, Open, Save
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        Gtk.StyleContext.add_class(btn_box.get_style_context(), "linked")

        self.btn_new = Gtk.Button.new_from_icon_name("document-new-symbolic", Gtk.IconSize.BUTTON)
        self.btn_new.set_tooltip_text("New Document (Ctrl+N)")
        self.btn_new.connect("clicked", lambda w: self.on_new())
        btn_box.pack_start(self.btn_new, False, False, 0)

        self.btn_open = Gtk.Button.new_from_icon_name("document-open-symbolic", Gtk.IconSize.BUTTON)
        self.btn_open.set_tooltip_text("Open File (Ctrl+O)")
        self.btn_open.connect("clicked", lambda w: self.on_open())
        btn_box.pack_start(self.btn_open, False, False, 0)

        self.btn_save = Gtk.Button.new_from_icon_name("document-save-symbolic", Gtk.IconSize.BUTTON)
        self.btn_save.set_tooltip_text("Save File (Ctrl+S)")
        self.btn_save.connect("clicked", lambda w: self.on_save())
        btn_box.pack_start(self.btn_save, False, False, 0)

        self.header.pack_start(btn_box)

        # Right controls: Zoom In/Out, Line Numbers Toggle, Search, Menu
        # Zoom controls (Retina scaling)
        zoom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        Gtk.StyleContext.add_class(zoom_box.get_style_context(), "linked")

        self.btn_zoom_out = Gtk.Button.new_from_icon_name("zoom-out-symbolic", Gtk.IconSize.BUTTON)
        self.btn_zoom_out.set_tooltip_text("Zoom Out (Ctrl+-)")
        self.btn_zoom_out.connect("clicked", lambda w: self.editor.zoom_out())
        zoom_box.pack_start(self.btn_zoom_out, False, False, 0)

        self.btn_zoom_reset = Gtk.Button(label="100%")
        self.btn_zoom_reset.set_tooltip_text("Reset Zoom / Retina 100% (Ctrl+0)")
        self.btn_zoom_reset.connect("clicked", lambda w: self.editor.reset_zoom())
        zoom_box.pack_start(self.btn_zoom_reset, False, False, 0)

        self.btn_zoom_in = Gtk.Button.new_from_icon_name("zoom-in-symbolic", Gtk.IconSize.BUTTON)
        self.btn_zoom_in.set_tooltip_text("Zoom In (Ctrl++)")
        self.btn_zoom_in.connect("clicked", lambda w: self.editor.zoom_in())
        zoom_box.pack_start(self.btn_zoom_in, False, False, 0)

        self.header.pack_end(self._build_menu_button())

        # Line numbers toggle button
        self.btn_line_numbers = Gtk.ToggleButton()
        self.btn_line_numbers.set_image(Gtk.Image.new_from_icon_name("format-indent-more-symbolic", Gtk.IconSize.BUTTON))
        self.btn_line_numbers.set_active(True)
        self.btn_line_numbers.set_tooltip_text("Toggle Line Numbers")
        self.btn_line_numbers.connect("toggled", self._on_toggle_line_numbers)
        self.header.pack_end(self.btn_line_numbers)

        # Find button
        self.btn_search = Gtk.Button.new_from_icon_name("edit-find-symbolic", Gtk.IconSize.BUTTON)
        self.btn_search.set_tooltip_text("Find and Replace (Ctrl+F)")
        self.btn_search.connect("clicked", lambda w: self.search_bar.show_find())
        self.header.pack_end(self.btn_search)

        self.header.pack_end(zoom_box)

    def _build_menu_button(self):
        """Constructs the application menu popover."""
        menu_button = Gtk.MenuButton()
        menu_button.set_image(Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON))
        menu_button.set_tooltip_text("Preferences and Options")

        menu = Gtk.Menu()

        # Save As
        item_save_as = Gtk.MenuItem(label="Save As...")
        item_save_as.connect("activate", lambda w: self.on_save_as())
        menu.append(item_save_as)

        # Go to Line
        item_goto = Gtk.MenuItem(label="Go to Line... (Ctrl+G)")
        item_goto.connect("activate", lambda w: self.on_goto_line())
        menu.append(item_goto)

        menu.append(Gtk.SeparatorMenuItem())

        # Word Wrap toggle
        self.menu_wrap = Gtk.CheckMenuItem(label="Word Wrap")
        self.menu_wrap.set_active(True)
        self.menu_wrap.connect("toggled", lambda w: self.editor.set_word_wrap(w.get_active()))
        menu.append(self.menu_wrap)

        # Highlight current line toggle
        self.menu_highlight_line = Gtk.CheckMenuItem(label="Highlight Current Line")
        self.menu_highlight_line.set_active(True)
        self.menu_highlight_line.connect("toggled", lambda w: self.editor.set_highlight_current_line(w.get_active()))
        menu.append(self.menu_highlight_line)

        # Font chooser
        item_font = Gtk.MenuItem(label="Font Selection...")
        item_font.connect("activate", lambda w: self.on_choose_font())
        menu.append(item_font)

        # Style Schemes submenu
        item_theme = Gtk.MenuItem(label="Color Theme")
        theme_menu = Gtk.Menu()
        manager = GtkSource.StyleSchemeManager.get_default()
        schemes = manager.get_scheme_ids()

        group = []
        for s_id in schemes:
            scheme_obj = manager.get_scheme(s_id)
            title = scheme_obj.get_name() if scheme_obj else s_id
            radio = Gtk.RadioMenuItem(group=group[0] if group else None, label=title)
            group.append(radio)
            if s_id in ('xed', 'classic'):
                radio.set_active(True)
            radio.connect("toggled", self._on_theme_selected, s_id)
            theme_menu.append(radio)

        item_theme.set_submenu(theme_menu)
        menu.append(item_theme)

        menu.append(Gtk.SeparatorMenuItem())

        # Retina Display Info
        item_retina_info = Gtk.MenuItem(label="Retina Vision / HiDPI Info")
        item_retina_info.connect("activate", lambda w: self.on_retina_info())
        menu.append(item_retina_info)

        # About
        item_about = Gtk.MenuItem(label="About RetinaPad")
        item_about.connect("activate", lambda w: self.on_about())
        menu.append(item_about)

        menu.show_all()
        menu_button.set_popup(menu)
        return menu_button

    def _build_editor_area(self):
        """Builds main editor container with embedded search revealer."""
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.editor = RetinaEditor()
        self.search_bar = SearchBar(self.editor)

        self.vbox.pack_start(self.search_bar, False, False, 0)
        self.vbox.pack_start(self.editor, True, True, 0)

        # Connect editor signals
        self.editor.connect("cursor-moved", self._on_cursor_moved)
        self.editor.connect("content-modified", self._on_content_modified)
        self.editor.connect("zoom-changed", self._on_zoom_changed)
        self.editor.connect("file-saved", self._on_file_saved)

        self.add(self.vbox)

    def _build_status_bar(self):
        """Status bar at bottom showing Ln/Col, counts, zoom, and encoding."""
        self.status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        self.status_bar.set_margin_start(12)
        self.status_bar.set_margin_end(12)
        self.status_bar.set_margin_top(4)
        self.status_bar.set_margin_bottom(4)

        # Left status label (Line & Column)
        self.lbl_pos = Gtk.Label(label="Ln 1, Col 1")
        self.lbl_pos.set_xalign(0)
        self.status_bar.pack_start(self.lbl_pos, False, False, 0)

        # Document stats (Lines, Words, Chars)
        self.lbl_stats = Gtk.Label(label="1 line, 0 words, 0 chars")
        self.lbl_stats.set_xalign(0)
        self.status_bar.pack_start(self.lbl_stats, False, False, 0)

        # Right status labels: Retina Zoom, Encoding
        self.lbl_encoding = Gtk.Label(label="UTF-8")
        self.status_bar.pack_end(self.lbl_encoding, False, False, 0)

        self.lbl_zoom = Gtk.Label(label="Retina: 100%")
        self.status_bar.pack_end(self.lbl_zoom, False, False, 0)

        self.vbox.pack_end(self.status_bar, False, False, 0)

    def _setup_shortcuts(self):
        """Keyboard accelerators for common actions."""
        accel_group = Gtk.AccelGroup()
        self.add_accel_group(accel_group)

        shortcuts = [
            ("n", Gdk.ModifierType.CONTROL_MASK, lambda: self.on_new()),
            ("o", Gdk.ModifierType.CONTROL_MASK, lambda: self.on_open()),
            ("s", Gdk.ModifierType.CONTROL_MASK, lambda: self.on_save()),
            ("s", Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK, lambda: self.on_save_as()),
            ("f", Gdk.ModifierType.CONTROL_MASK, lambda: self.search_bar.show_find()),
            ("h", Gdk.ModifierType.CONTROL_MASK, lambda: self.search_bar.show_replace()),
            ("g", Gdk.ModifierType.CONTROL_MASK, lambda: self.on_goto_line()),
            ("plus", Gdk.ModifierType.CONTROL_MASK, lambda: self.editor.zoom_in()),
            ("equal", Gdk.ModifierType.CONTROL_MASK, lambda: self.editor.zoom_in()),
            ("minus", Gdk.ModifierType.CONTROL_MASK, lambda: self.editor.zoom_out()),
            ("0", Gdk.ModifierType.CONTROL_MASK, lambda: self.editor.reset_zoom()),
            ("q", Gdk.ModifierType.CONTROL_MASK, lambda: self.close()),
            ("w", Gdk.ModifierType.CONTROL_MASK, lambda: self.close()),
        ]

        for key_str, mod, callback in shortcuts:
            keyval = Gdk.keyval_from_name(key_str)
            accel_group.connect(keyval, mod, Gtk.AccelFlags.VISIBLE, lambda ag, w, kv, m, cb=callback: cb())

    # --------------------------------------------------------------------------
    # Signal Handlers & Updates
    # --------------------------------------------------------------------------
    def _on_cursor_moved(self, editor, line, col):
        self.lbl_pos.set_text(f"Ln {line}, Col {col}")
        stats = self.editor.get_document_statistics()
        self.lbl_stats.set_text(f"{stats['total_lines']} lines, {stats['word_count']} words, {stats['char_count']} chars")

    def _on_content_modified(self, editor, is_modified):
        self.update_title()
        stats = self.editor.get_document_statistics()
        self.lbl_stats.set_text(f"{stats['total_lines']} lines, {stats['word_count']} words, {stats['char_count']} chars")

    def _on_zoom_changed(self, editor, percent):
        self.btn_zoom_reset.set_label(f"{percent}%")
        self.lbl_zoom.set_text(f"Retina: {percent}%")

    def _on_file_saved(self, editor, path):
        self.current_filename = os.path.basename(path)
        self.update_title()
        self.lbl_encoding.set_text(self.editor.file_encoding)

    def _on_toggle_line_numbers(self, button):
        self.editor.set_show_line_numbers(button.get_active())

    def _on_theme_selected(self, radio_item, scheme_id):
        if radio_item.get_active():
            self.editor.set_theme(scheme_id)

    def update_title(self):
        mod_prefix = "● " if self.editor.is_modified() else ""
        file_display = self.current_filename if self.editor.file_path else "Untitled"
        self.header.set_subtitle(f"{mod_prefix}{file_display}")
        self.set_title(f"{mod_prefix}{file_display} - {self.APP_NAME}")

    # --------------------------------------------------------------------------
    # File Operations
    # --------------------------------------------------------------------------
    def on_new(self):
        if not self._check_unsaved_changes():
            return
        self.editor.file_path = None
        self.editor.set_text("")
        self.current_filename = "Untitled Document"
        self.update_title()

    def on_open(self):
        if not self._check_unsaved_changes():
            return

        dialog = Gtk.FileChooserNative.new(
            "Open File",
            self,
            Gtk.FileChooserAction.OPEN,
            "_Open",
            "_Cancel"
        )
        self._add_file_filters(dialog)

        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            path = dialog.get_filename()
            self.open_path(path)
        dialog.destroy()

    def open_path(self, path):
        try:
            self.editor.load_file(path)
            self.current_filename = os.path.basename(path)
            self.update_title()
            self.lbl_encoding.set_text(self.editor.file_encoding)
        except Exception as e:
            self._show_error_dialog(f"Could not open file:\n{e}")

    def on_save(self):
        if not self.editor.file_path:
            return self.on_save_as()
        try:
            self.editor.save_file()
            return True
        except Exception as e:
            self._show_error_dialog(f"Could not save file:\n{e}")
            return False

    def on_save_as(self):
        dialog = Gtk.FileChooserNative.new(
            "Save As",
            self,
            Gtk.FileChooserAction.SAVE,
            "_Save",
            "_Cancel"
        )
        dialog.set_do_overwrite_confirmation(True)
        if self.editor.file_path:
            dialog.set_filename(self.editor.file_path)
        else:
            dialog.set_current_name("Untitled.txt")
        self._add_file_filters(dialog)

        response = dialog.run()
        success = False
        if response == Gtk.ResponseType.ACCEPT:
            path = dialog.get_filename()
            try:
                self.editor.save_file(path)
                success = True
            except Exception as e:
                self._show_error_dialog(f"Could not save file:\n{e}")
        dialog.destroy()
        return success

    def _add_file_filters(self, dialog):
        filter_text = Gtk.FileFilter()
        filter_text.set_name("Text Files (*.txt, *.md, *.py, ...)")
        filter_text.add_mime_type("text/*")
        filter_text.add_pattern("*.txt")
        filter_text.add_pattern("*.md")
        filter_text.add_pattern("*.py")
        filter_text.add_pattern("*.sh")
        filter_text.add_pattern("*.json")
        dialog.add_filter(filter_text)

        filter_all = Gtk.FileFilter()
        filter_all.set_name("All Files")
        filter_all.add_pattern("*")
        dialog.add_filter(filter_all)

    def _check_unsaved_changes(self):
        if not self.editor.is_modified():
            return True

        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE,
            text=f"Save changes to \"{self.current_filename}\" before closing?"
        )
        dialog.format_secondary_text("If you close without saving, your changes will be discarded.")
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Discard Changes", Gtk.ResponseType.NO)
        dialog.add_button("Save", Gtk.ResponseType.YES)
        dialog.set_default_response(Gtk.ResponseType.YES)

        resp = dialog.run()
        dialog.destroy()

        if resp == Gtk.ResponseType.YES:
            return self.on_save()
        elif resp == Gtk.ResponseType.NO:
            return True
        else:
            return False

    def _on_delete_event(self, widget, event):
        if self._check_unsaved_changes():
            return False  # Proceed with closing
        return True  # Block closing

    # --------------------------------------------------------------------------
    # Dialogs & Menus
    # --------------------------------------------------------------------------
    def on_goto_line(self):
        dialog = Gtk.Dialog(
            title="Go to Line",
            transient_for=self,
            flags=Gtk.DialogFlags.MODAL,
            buttons=("Cancel", Gtk.ResponseType.CANCEL, "Go to Line", Gtk.ResponseType.OK)
        )
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_border_width(12)

        content = dialog.get_content_area()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label="Line number:")
        entry = Gtk.SpinButton()
        stats = self.editor.get_document_statistics()
        entry.set_range(1, max(1, stats['total_lines']))
        entry.set_increments(1, 10)
        entry.set_value(stats['line'])
        entry.set_activates_default(True)

        box.pack_start(lbl, False, False, 0)
        box.pack_start(entry, True, True, 0)
        content.add(box)
        dialog.show_all()

        if dialog.run() == Gtk.ResponseType.OK:
            target_line = int(entry.get_value())
            self.editor.goto_line(target_line)
        dialog.destroy()

    def on_choose_font(self):
        dialog = Gtk.FontChooserDialog(title="Select Retina Font", transient_for=self)
        dialog.set_font(f"{self.editor.base_font_family} {self.editor.base_font_size}")
        if dialog.run() == Gtk.ResponseType.OK:
            font_desc = dialog.get_font_desc()
            family = font_desc.get_family()
            size = font_desc.get_size() // Pango.SCALE
            self.editor.set_font_family_and_size(family, size)
        dialog.destroy()

    def on_retina_info(self):
        """Display Retina and HiDPI display diagnostics for Linux Mint Cinnamon."""
        window = self.get_window()
        scale_factor = window.get_scale_factor() if window else 1
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or (display.get_monitor(0) if display.get_n_monitors() > 0 else None)

        if monitor:
            geom = monitor.get_geometry()
            res_str = f"{geom.width}x{geom.height}"
            scale = monitor.get_scale_factor()
            model = monitor.get_model() or "Standard Monitor"
        else:
            res_str = "Unknown"
            scale = scale_factor
            model = "Default"

        info_text = (
            f"<b>Retina Vision & Display Details:</b>\n\n"
            f"• <b>Hardware Display Scale:</b> {scale}x ({'HiDPI / Retina Active' if scale > 1 else 'Standard DPI'})\n"
            f"• <b>Active Resolution:</b> {res_str}\n"
            f"• <b>Monitor:</b> {model}\n"
            f"• <b>Current Editor Zoom:</b> {self.editor.get_zoom_percent()}%\n"
            f"• <b>Font Subpixel Antialiasing:</b> Cairo RGBA Subpixel Enabled\n\n"
            f"<i>Tip for Linux Mint Cinnamon:</i>\n"
            f"You can adjust system-wide HiDPI scaling in <b>Cinnamon Settings → General → Desktop Scaling</b> (Normal or Double), "
            f"or use RetinaPad's real-time <b>Ctrl + Scroll Wheel</b> for smooth font magnification."
        )

        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Retina Vision & Display Diagnostics"
        )
        dialog.set_markup(info_text)
        dialog.run()
        dialog.destroy()

    def on_about(self):
        dialog = Gtk.AboutDialog(transient_for=self)
        dialog.set_program_name(self.APP_NAME)
        dialog.set_version(self.APP_VERSION)
        dialog.set_comments(
            "A fast, elegant notepad with Retina Vision (HiDPI dynamic font scaling, subpixel rendering) "
            "and line numbers, tailored for Linux Mint Cinnamon."
        )
        dialog.set_website_label("RetinaPad on Linux Mint")
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "retinapad.svg")
        if os.path.exists(icon_path):
            dialog.set_logo(GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_path, 96, 96, True))
        dialog.run()
        dialog.destroy()

    def _show_error_dialog(self, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="RetinaPad Error"
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()


class RetinaPadApp(Gtk.Application):
    """Gtk.Application implementation for RetinaPad."""

    def __init__(self):
        super().__init__(
            application_id="org.linuxmint.retinapad",
            flags=Gio.ApplicationFlags.HANDLES_OPEN | Gio.ApplicationFlags.NON_UNIQUE
        )
        self.file_to_open = None

    def do_activate(self):
        win = RetinaPadWindow(self, file_path=self.file_to_open)
        win.present()

    def do_open(self, files, n_files, hint):
        for f in files:
            path = f.get_path()
            win = RetinaPadWindow(self, file_path=path)
            win.present()


def main():
    app = RetinaPadApp()
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        app.file_to_open = os.path.abspath(sys.argv[1])
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
