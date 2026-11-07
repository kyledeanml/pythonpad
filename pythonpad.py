#!/usr/bin/env python3
"""
PythonPad - Python IDE and Code Editor
With Retina Vision, Line Numbers, Interactive Python Shell,
Advanced Code Editing Tools, and System Base Python Interpreter Execution.
Designed for Linux Mint Cinnamon.
"""

import sys
import os
import shlex

sys.dont_write_bytecode = True
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
gi.require_version('GtkSource', '4')
gi.require_version('Pango', '1.0')

from gi.repository import Gtk, Gdk, GdkPixbuf, GtkSource, Pango, GLib, Gio
from editor import RetinaEditor
from search_bar import SearchBar
from pylint_panel import PythonPadPanel
from python_tools import InterpreterManager, PythonLinter


class PythonPadWindow(Gtk.ApplicationWindow):
    """Main application window for PythonPad."""

    APP_NAME = "PythonPad"
    APP_VERSION = "2.1"

    def __init__(self, app, initial_files=None):
        super().__init__(application=app, title=self.APP_NAME)
        self.set_default_size(1050, 720)
        self.set_position(Gtk.WindowPosition.CENTER)
        self._stats_timeout_id = None

        # Set application & window icon for Cinnamon panel, alt-tab, and taskbar
        self.set_wmclass("pythonpad", "PythonPad")
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pythonpad.svg")
        if os.path.exists(icon_path):
            try:
                Gtk.Window.set_default_icon_from_file(icon_path)
                self.set_icon_from_file(icon_path)
                pixbufs = [
                    GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_path, sz, sz, True)
                    for sz in (16, 24, 32, 48, 64, 128, 256)
                ]
                Gtk.Window.set_default_icon_list(pixbufs)
                self.set_icon_list(pixbufs)
            except Exception:
                pass

        # Dark mode preference & neon blue theme
        settings = Gtk.Settings.get_default()
        if settings:
            settings.set_property("gtk-application-prefer-dark-theme", True)
        self.current_theme = "pythonpad-neon"
        self._apply_dark_neon_theme()

        # UI Construction
        self._build_header_bar()
        self._build_editor_area()
        self._build_status_bar()
        self._setup_shortcuts()

        self.connect("delete-event", self._on_delete_event)

        # Open initial files or blank tab
        if initial_files:
            for f in initial_files:
                self.new_tab(f)
        if self.notebook_tabs.get_n_pages() == 0:
            self.new_tab()

        self.show_all()
        self.search_bar.set_reveal_child(False)

    def _apply_dark_neon_theme(self):
        """Apply sleek dark mode CSS with white text and neon blue accents across the UI."""
        styles_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles")
        if os.path.exists(styles_dir):
            GtkSource.StyleSchemeManager.get_default().prepend_search_path(styles_dir)

        css = b"""
        /* PythonPad Dark Neon Theme */
        window, dialog, .background {
            background-color: #0b0f19;
            color: #ffffff;
        }

        headerbar {
            background: linear-gradient(to bottom, #111827, #0b0f19);
            border-bottom: 1px solid rgba(0, 240, 255, 0.35);
            box-shadow: 0 1px 6px rgba(0, 240, 255, 0.12);
            color: #ffffff;
            padding: 4px 6px;
        }
        headerbar .title {
            color: #ffffff;
            font-weight: bold;
        }
        headerbar .subtitle {
            color: #38bdf8;
            font-size: 85%;
        }

        button {
            background-color: #131d33;
            color: #ffffff;
            border: 1px solid rgba(0, 240, 255, 0.25);
            border-radius: 4px;
            padding: 4px 8px;
            transition: all 150ms ease;
        }
        button:hover {
            background-color: #1a2744;
            border-color: #00f0ff;
            color: #00f0ff;
            box-shadow: 0 0 6px rgba(0, 240, 255, 0.35);
        }
        button:checked, button:active {
            background-color: #034b75;
            border-color: #00f0ff;
            color: #ffffff;
            box-shadow: 0 0 8px rgba(0, 240, 255, 0.45);
        }

        .linked > button {
            border-color: rgba(0, 240, 255, 0.25);
        }
        .linked > button:hover {
            border-color: #00f0ff;
        }

        notebook {
            background-color: #070a14;
        }
        notebook > header {
            background-color: #070a14;
            border-bottom: 1px solid rgba(0, 240, 255, 0.2);
        }
        notebook tab {
            background-color: #0b0f19;
            color: #94a3b8;
            border: 1px solid rgba(0, 240, 255, 0.15);
            border-bottom: none;
            padding: 5px 12px;
            margin-right: 2px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
        }
        notebook tab:hover {
            background-color: #131d33;
            color: #e0f2fe;
            border-color: rgba(0, 240, 255, 0.4);
        }
        notebook tab:checked {
            background-color: #0a0e1a;
            color: #ffffff;
            border-color: #00f0ff;
            border-top: 2px solid #00f0ff;
            box-shadow: inset 0 2px 0 #00f0ff;
        }
        notebook tab label {
            color: inherit;
            font-weight: 500;
        }
        notebook tab button {
            background: transparent;
            border: none;
            color: #94a3b8;
            padding: 0 2px;
            min-height: 16px;
            min-width: 16px;
        }
        notebook tab button:hover {
            color: #00f0ff;
            background-color: rgba(0, 240, 255, 0.15);
            border-radius: 3px;
        }

        paned > separator {
            background-color: #070a14;
            border-top: 1px solid rgba(0, 240, 255, 0.3);
            border-bottom: 1px solid rgba(0, 240, 255, 0.3);
            min-height: 6px;
        }
        paned > separator:hover {
            background-color: #00f0ff;
            box-shadow: 0 0 8px rgba(0, 240, 255, 0.6);
        }

        .statusbar, #statusbar {
            background-color: #070a14;
            border-top: 1px solid rgba(0, 240, 255, 0.2);
            color: #94a3b8;
            padding: 2px 8px;
        }
        .statusbar label, #statusbar label {
            color: #cbd5e1;
            font-size: 88%;
        }

        .search-bar {
            background-color: #0d1322;
            border-bottom: 1px solid rgba(0, 240, 255, 0.25);
        }
        .bottom-panel-bar {
            background-color: #0a0e1a;
            border-bottom: 1px solid rgba(0, 240, 255, 0.2);
        }

        label.shell-prompt {
            color: #00f0ff;
            font-weight: bold;
        }

        entry {
            background-color: #0a0e1a;
            color: #ffffff;
            border: 1px solid rgba(0, 240, 255, 0.3);
            border-radius: 4px;
            padding: 4px 8px;
        }
        entry:focus {
            border-color: #00f0ff;
            box-shadow: 0 0 5px rgba(0, 240, 255, 0.4);
        }

        textview, textview text {
            background-color: #0a0e1a;
            color: #ffffff;
        }

        menu, .menu {
            background-color: #0d1322;
            color: #ffffff;
            border: 1px solid rgba(0, 240, 255, 0.35);
            padding: 4px;
        }
        menuitem {
            color: #e0f2fe;
            padding: 4px 10px;
        }
        menuitem:hover {
            background-color: #034b75;
            color: #ffffff;
        }
        menuitem:disabled {
            color: #475569;
        }

        treeview {
            background-color: #0a0e1a;
            color: #f8fafc;
            border: none;
        }
        treeview:selected {
            background-color: #034b75;
            color: #ffffff;
        }
        treeview header button {
            background-color: #0d1322;
            color: #00f0ff;
            border-bottom: 1px solid rgba(0, 240, 255, 0.3);
            font-weight: bold;
        }

        scrollbar {
            background-color: #070a14;
        }
        scrollbar slider {
            background-color: #1e293b;
            border-radius: 4px;
            min-width: 8px;
            min-height: 8px;
        }
        scrollbar slider:hover {
            background-color: #0284c7;
        }
        scrollbar slider:active {
            background-color: #00f0ff;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        screen = Gdk.Screen.get_default()
        if screen:
            Gtk.StyleContext.add_provider_for_screen(
                screen,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    # --------------------------------------------------------------------------
    # Header Bar
    # --------------------------------------------------------------------------
    def _build_header_bar(self):
        self.header = Gtk.HeaderBar()
        self.header.set_show_close_button(True)
        self.header.set_title(self.APP_NAME)
        self.header.set_subtitle("Python Development Environment")
        self.set_titlebar(self.header)

        # File actions: New, Open, Save
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        Gtk.StyleContext.add_class(btn_box.get_style_context(), "linked")

        self.btn_new = Gtk.Button.new_from_icon_name("document-new-symbolic", Gtk.IconSize.BUTTON)
        self.btn_new.set_tooltip_text("New Document (Ctrl+N or Ctrl+T)")
        self.btn_new.connect("clicked", lambda w: self.new_tab())
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

        # Right Controls: Menu, Line Numbers, Python Execution, Search, Zoom
        self.header.pack_end(self._build_menu_button())

        # Line numbers toggle
        self.btn_line_numbers = Gtk.ToggleButton()
        self.btn_line_numbers.set_image(Gtk.Image.new_from_icon_name("format-indent-more-symbolic", Gtk.IconSize.BUTTON))
        self.btn_line_numbers.set_active(True)
        self.btn_line_numbers.set_tooltip_text("Toggle Line Numbers")
        self.btn_line_numbers.connect("toggled", self._on_toggle_line_numbers)
        self.header.pack_end(self.btn_line_numbers)

        # Python Run / Shell / Lint Button Group
        py_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        Gtk.StyleContext.add_class(py_box.get_style_context(), "linked")

        # Run Module (F5)
        self.btn_run = Gtk.Button.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.BUTTON)
        self.btn_run.set_tooltip_text("Run Script in Base Interpreter (F5)")
        self.btn_run.connect("clicked", lambda w: self.run_active_script())
        py_box.pack_start(self.btn_run, False, False, 0)

        # Interactive Shell (REPL)
        self.btn_shell = Gtk.Button.new_from_icon_name("utilities-terminal-symbolic", Gtk.IconSize.BUTTON)
        self.btn_shell.set_tooltip_text("Interactive Python Shell")
        self.btn_shell.connect("clicked", lambda w: self.toggle_bottom_panel(tab_index=0))
        py_box.pack_start(self.btn_shell, False, False, 0)

        # Pylint / Diagnostics (F8)
        self.btn_lint = Gtk.Button.new_from_icon_name("system-run-symbolic", Gtk.IconSize.BUTTON)
        self.btn_lint.set_tooltip_text("Pylint Diagnostics & Syntax Check (F8)")
        self.btn_lint.connect("clicked", lambda w: self.toggle_bottom_panel(tab_index=2))
        py_box.pack_start(self.btn_lint, False, False, 0)

        self.header.pack_end(py_box)

        # Find button
        self.btn_search = Gtk.Button.new_from_icon_name("edit-find-symbolic", Gtk.IconSize.BUTTON)
        self.btn_search.set_tooltip_text("Find and Replace (Ctrl+F)")
        self.btn_search.connect("clicked", lambda w: self.on_show_find())
        self.header.pack_end(self.btn_search)

        # Retina Zoom Group
        zoom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        Gtk.StyleContext.add_class(zoom_box.get_style_context(), "linked")

        self.btn_zoom_out = Gtk.Button.new_from_icon_name("zoom-out-symbolic", Gtk.IconSize.BUTTON)
        self.btn_zoom_out.set_tooltip_text("Retina Zoom Out (Ctrl+-)")
        self.btn_zoom_out.connect("clicked", lambda w: self.zoom_active(out=True))
        zoom_box.pack_start(self.btn_zoom_out, False, False, 0)

        self.btn_zoom_reset = Gtk.Button(label="100%")
        self.btn_zoom_reset.set_tooltip_text("Reset Retina Zoom (Ctrl+0)")
        self.btn_zoom_reset.connect("clicked", lambda w: self.zoom_active(reset=True))
        zoom_box.pack_start(self.btn_zoom_reset, False, False, 0)

        self.btn_zoom_in = Gtk.Button.new_from_icon_name("zoom-in-symbolic", Gtk.IconSize.BUTTON)
        self.btn_zoom_in.set_tooltip_text("Retina Zoom In (Ctrl++)")
        self.btn_zoom_in.connect("clicked", lambda w: self.zoom_active(out=False))
        zoom_box.pack_start(self.btn_zoom_in, False, False, 0)

        self.header.pack_end(zoom_box)

    def _build_menu_button(self):
        menu_button = Gtk.MenuButton()
        menu_button.set_image(Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON))
        menu_button.set_tooltip_text("Menu and Tools")

        menu = Gtk.Menu()

        # File
        item_save_as = Gtk.MenuItem(label="Save As... (Ctrl+Shift+S)")
        item_save_as.connect("activate", lambda w: self.on_save_as())
        menu.append(item_save_as)

        item_close_tab = Gtk.MenuItem(label="Close Tab (Ctrl+W)")
        item_close_tab.connect("activate", lambda w: self.close_current_tab())
        menu.append(item_close_tab)

        menu.append(Gtk.SeparatorMenuItem())

        # Python Execution Submenu
        item_run_sub = Gtk.MenuItem(label="Python Execution")
        run_menu = Gtk.Menu()

        it_run = Gtk.MenuItem(label="Run Module (F5)")
        it_run.connect("activate", lambda w: self.run_active_script())
        run_menu.append(it_run)

        it_run_args = Gtk.MenuItem(label="Run with Arguments... (Shift+F5)")
        it_run_args.connect("activate", lambda w: self.on_run_with_args())
        run_menu.append(it_run_args)

        it_check = Gtk.MenuItem(label="Check Module Syntax (Alt+X)")
        it_check.connect("activate", lambda w: self.on_check_syntax())
        run_menu.append(it_check)

        it_shell = Gtk.MenuItem(label="Python Interactive Shell")
        it_shell.connect("activate", lambda w: self.toggle_bottom_panel(force_show=True, tab_index=0))
        run_menu.append(it_shell)

        it_restart = Gtk.MenuItem(label="Restart Shell (Ctrl+F6)")
        it_restart.connect("activate", lambda w: self.panel.restart_shell())
        run_menu.append(it_restart)

        it_interp = Gtk.MenuItem(label="Select Python Interpreter...")
        it_interp.connect("activate", lambda w: self.on_select_interpreter())
        run_menu.append(it_interp)

        item_run_sub.set_submenu(run_menu)
        menu.append(item_run_sub)

        # Advanced Code Editing Submenu
        item_edit_sub = Gtk.MenuItem(label="Code Editing Tools")
        edit_menu = Gtk.Menu()

        it_dup = Gtk.MenuItem(label="Duplicate Line (Ctrl+D)")
        it_dup.connect("activate", lambda w: self._call_editor("duplicate_line"))
        edit_menu.append(it_dup)

        it_del = Gtk.MenuItem(label="Delete Line (Ctrl+Shift+K)")
        it_del.connect("activate", lambda w: self._call_editor("delete_line"))
        edit_menu.append(it_del)

        it_comm = Gtk.MenuItem(label="Toggle Line Comment (Ctrl+/)")
        it_comm.connect("activate", lambda w: self._call_editor("toggle_comment"))
        edit_menu.append(it_comm)

        it_up = Gtk.MenuItem(label="Move Line Up (Alt+Up)")
        it_up.connect("activate", lambda w: self._call_editor("move_line_up"))
        edit_menu.append(it_up)

        it_down = Gtk.MenuItem(label="Move Line Down (Alt+Down)")
        it_down.connect("activate", lambda w: self._call_editor("move_line_down"))
        edit_menu.append(it_down)

        it_join = Gtk.MenuItem(label="Join Lines (Ctrl+J)")
        it_join.connect("activate", lambda w: self._call_editor("join_lines"))
        edit_menu.append(it_join)

        it_upper = Gtk.MenuItem(label="Convert to UPPERCASE (Ctrl+Shift+U)")
        it_upper.connect("activate", lambda w: self._call_editor("convert_case", True))
        edit_menu.append(it_upper)

        it_lower = Gtk.MenuItem(label="Convert to lowercase (Ctrl+U)")
        it_lower.connect("activate", lambda w: self._call_editor("convert_case", False))
        edit_menu.append(it_lower)

        item_edit_sub.set_submenu(edit_menu)
        menu.append(item_edit_sub)

        menu.append(Gtk.SeparatorMenuItem())

        # Go to Line
        item_goto = Gtk.MenuItem(label="Go to Line... (Ctrl+G)")
        item_goto.connect("activate", lambda w: self.on_goto_line())
        menu.append(item_goto)

        # Word Wrap
        self.menu_wrap = Gtk.CheckMenuItem(label="Word Wrap")
        self.menu_wrap.set_active(True)
        self.menu_wrap.connect("toggled", lambda w: self._set_all_word_wrap(w.get_active()))
        menu.append(self.menu_wrap)

        # Font Selection
        item_font = Gtk.MenuItem(label="Font Selection...")
        item_font.connect("activate", lambda w: self.on_choose_font())
        menu.append(item_font)

        # Color Themes
        item_theme = Gtk.MenuItem(label="Color Theme")
        theme_menu = Gtk.Menu()
        manager = GtkSource.StyleSchemeManager.get_default()
        group = []
        neon_radio = None
        for s_id in manager.get_scheme_ids():
            scheme_obj = manager.get_scheme(s_id)
            title = scheme_obj.get_name() if scheme_obj else s_id
            radio = Gtk.RadioMenuItem(group=group[0] if group else None, label=title)
            group.append(radio)
            if s_id == 'pythonpad-neon':
                neon_radio = radio
            radio.connect("toggled", self._on_theme_selected, s_id)
            theme_menu.append(radio)
        if neon_radio:
            neon_radio.set_active(True)
        item_theme.set_submenu(theme_menu)
        menu.append(item_theme)

        menu.append(Gtk.SeparatorMenuItem())

        # Retina Diagnostics
        item_retina_info = Gtk.MenuItem(label="Retina Vision / HiDPI Info")
        item_retina_info.connect("activate", lambda w: self.on_retina_info())
        menu.append(item_retina_info)

        # About
        item_about = Gtk.MenuItem(label="About PythonPad")
        item_about.connect("activate", lambda w: self.on_about())
        menu.append(item_about)

        menu.show_all()
        menu_button.set_popup(menu)
        return menu_button

    # --------------------------------------------------------------------------
    # Editor & Tabs Area
    # --------------------------------------------------------------------------
    def _build_editor_area(self):
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Search Bar
        self.search_bar = SearchBar(None)
        self.vbox.pack_start(self.search_bar, False, False, 0)

        # Vertical paned: Editor Tabs on top, PythonPadPanel on bottom
        self.paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)

        # Multi-tab Notebook
        self.notebook_tabs = Gtk.Notebook()
        self.notebook_tabs.set_scrollable(True)
        self.notebook_tabs.connect("switch-page", self._on_tab_switched)
        self.paned.pack1(self.notebook_tabs, resize=True, shrink=False)

        # Bottom Panel (Shell, Runner, Linter)
        self.panel = PythonPadPanel(lambda: self.get_current_editor())
        self.panel.connect("goto-location", lambda p, l, c: self._goto_editor_location(l, c))
        self.panel.connect("close-requested", lambda p: self.toggle_bottom_panel(force_show=False))
        self.panel.set_no_show_all(True)
        self.panel.set_visible(False)
        self.paned.pack2(self.panel, resize=False, shrink=True)

        self.vbox.pack_start(self.paned, True, True, 0)
        self.add(self.vbox)

    def _build_status_bar(self):
        self.status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        self.status_bar.set_name("statusbar")
        Gtk.StyleContext.add_class(self.status_bar.get_style_context(), "statusbar")
        self.status_bar.set_margin_start(12)
        self.status_bar.set_margin_end(12)
        self.status_bar.set_margin_top(4)
        self.status_bar.set_margin_bottom(4)

        # Left: Ln / Col
        self.lbl_pos = Gtk.Label(label="Ln 1, Col 1")
        self.lbl_pos.set_xalign(0)
        self.status_bar.pack_start(self.lbl_pos, False, False, 0)

        # Counts
        self.lbl_stats = Gtk.Label(label="1 line, 0 words, 0 chars")
        self.lbl_stats.set_xalign(0)
        self.status_bar.pack_start(self.lbl_stats, False, False, 0)

        # Right: Python Interpreter, Encoding, Zoom
        interp_name = InterpreterManager.get_interpreter_version()
        self.lbl_interp = Gtk.Label(label=f"Python: {interp_name} (Base)")
        self.status_bar.pack_end(self.lbl_interp, False, False, 0)

        self.lbl_encoding = Gtk.Label(label="UTF-8 | LF")
        self.status_bar.pack_end(self.lbl_encoding, False, False, 0)

        self.lbl_zoom = Gtk.Label(label="Retina: 100%")
        self.status_bar.pack_end(self.lbl_zoom, False, False, 0)

        self.vbox.pack_end(self.status_bar, False, False, 0)

    # --------------------------------------------------------------------------
    # Tab Management
    # --------------------------------------------------------------------------
    def new_tab(self, file_path=None):
        """Create and append a new document tab with a RetinaEditor, or focus if already open."""
        if file_path:
            abs_path = os.path.abspath(os.path.expanduser(file_path))
            for i in range(self.notebook_tabs.get_n_pages()):
                existing = self.notebook_tabs.get_nth_page(i)
                if existing.file_path and os.path.abspath(existing.file_path) == abs_path:
                    self.notebook_tabs.set_current_page(i)
                    return existing

            # Reuse single untouched Untitled tab if present
            if self.notebook_tabs.get_n_pages() == 1:
                first_ed = self.notebook_tabs.get_nth_page(0)
                if not first_ed.file_path and not first_ed.is_modified() and first_ed.source_buffer.get_char_count() == 0:
                    try:
                        if os.path.isfile(abs_path):
                            first_ed.load_file(abs_path)
                        else:
                            first_ed.file_path = abs_path
                            first_ed.set_syntax_from_filename(abs_path)
                        self._update_tab_label(first_ed)
                        self.update_title()
                        self._schedule_stats_update(first_ed, immediate=True)
                        return first_ed
                    except Exception as e:
                        self._show_error(f"Could not open file:\n{e}")
                        return first_ed

        try:
            editor = RetinaEditor(file_path=file_path)
        except Exception as e:
            self._show_error(f"Could not open file:\n{e}")
            return None

        if hasattr(self, 'current_theme') and self.current_theme:
            editor.set_theme(self.current_theme)
        if hasattr(self, 'btn_line_numbers'):
            editor.set_show_line_numbers(self.btn_line_numbers.get_active())
        if hasattr(self, 'menu_wrap'):
            editor.set_word_wrap(self.menu_wrap.get_active())

        editor.connect("cursor-moved", self._on_cursor_moved)
        editor.connect("content-modified", self._on_content_modified)
        editor.connect("zoom-changed", self._on_zoom_changed)
        editor.connect("file-saved", self._on_file_saved)

        # Tab label header with title and close button
        title = os.path.basename(editor.file_path) if editor.file_path else "Untitled"
        tab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)

        lbl_title = Gtk.Label(label=title)
        tab_box.pack_start(lbl_title, False, False, 0)

        btn_close = Gtk.Button.new_from_icon_name("window-close-symbolic", Gtk.IconSize.MENU)
        btn_close.set_relief(Gtk.ReliefStyle.NONE)
        btn_close.set_focus_on_click(False)
        btn_close.connect("clicked", lambda b: self.close_tab_by_editor(editor))
        tab_box.pack_start(btn_close, False, False, 0)
        tab_box.show_all()

        page_num = self.notebook_tabs.append_page(editor, tab_box)
        editor.show_all()
        self.notebook_tabs.set_current_page(page_num)
        self.search_bar.set_editor(editor)
        self.update_title()
        self._schedule_stats_update(editor, immediate=True)
        return editor

    def get_current_editor(self):
        page_num = self.notebook_tabs.get_current_page()
        if page_num != -1:
            return self.notebook_tabs.get_nth_page(page_num)
        return None

    def close_current_tab(self):
        page_num = self.notebook_tabs.get_current_page()
        if page_num != -1:
            self.close_tab(page_num)

    def close_tab_by_editor(self, editor):
        page_num = self.notebook_tabs.page_num(editor)
        if page_num != -1:
            self.close_tab(page_num)

    def close_tab(self, page_num):
        editor = self.notebook_tabs.get_nth_page(page_num)
        if not editor:
            return

        if editor.is_modified():
            fname = os.path.basename(editor.file_path) if editor.file_path else "Untitled"
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.NONE,
                text=f"Save changes to \"{fname}\" before closing?"
            )
            dialog.format_secondary_text("Unsaved changes will be discarded.")
            dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
            dialog.add_button("Discard Changes", Gtk.ResponseType.NO)
            dialog.add_button("Save", Gtk.ResponseType.YES)
            resp = dialog.run()
            dialog.destroy()

            if resp == Gtk.ResponseType.YES:
                if not self.on_save(editor):
                    return
            elif resp != Gtk.ResponseType.NO:
                # Cancel or Escape/Delete-Event safely aborts closing
                return

        self.notebook_tabs.remove_page(page_num)
        if self.notebook_tabs.get_n_pages() == 0:
            self.new_tab()
        else:
            self.update_title()

    def _on_tab_switched(self, notebook, page, page_num):
        editor = page if isinstance(page, RetinaEditor) else self.get_current_editor()
        if editor:
            self.search_bar.set_editor(editor)
            self.update_title()
            line, col = editor.get_cursor_position()
            self.lbl_pos.set_text(f"Ln {line}, Col {col}")
            self.lbl_encoding.set_text(f"{editor.file_encoding} | {editor.line_ending}")
            self._schedule_stats_update(editor, immediate=True)
            percent = editor.get_zoom_percent()
            self.btn_zoom_reset.set_label(f"{percent}%")
            self.lbl_zoom.set_text(f"Retina: {percent}%")

    def _call_editor(self, method_name, *args):
        ed = self.get_current_editor()
        if ed and hasattr(ed, method_name):
            getattr(ed, method_name)(*args)

    def _goto_editor_location(self, line, col):
        ed = self.get_current_editor()
        if ed:
            ed.goto_line_col(line, col)

    # --------------------------------------------------------------------------
    # Keyboard Shortcuts
    # --------------------------------------------------------------------------
    def _setup_shortcuts(self):
        accel_group = Gtk.AccelGroup()
        self.add_accel_group(accel_group)

        shortcuts = [
            # File & Tabs
            ("n", Gdk.ModifierType.CONTROL_MASK, lambda: self.new_tab()),
            ("t", Gdk.ModifierType.CONTROL_MASK, lambda: self.new_tab()),
            ("o", Gdk.ModifierType.CONTROL_MASK, lambda: self.on_open()),
            ("s", Gdk.ModifierType.CONTROL_MASK, lambda: self.on_save()),
            ("s", Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK, lambda: self.on_save_as()),
            ("w", Gdk.ModifierType.CONTROL_MASK, lambda: self.close_current_tab()),
            ("q", Gdk.ModifierType.CONTROL_MASK, lambda: self.close()),

            # Python Execution
            ("F5", 0, lambda: self.run_active_script()),
            ("F5", Gdk.ModifierType.SHIFT_MASK, lambda: self.on_run_with_args()),
            ("x", Gdk.ModifierType.MOD1_MASK, lambda: self.on_check_syntax()),
            ("F6", Gdk.ModifierType.CONTROL_MASK, lambda: self.panel.restart_shell()),
            ("F8", 0, lambda: self.toggle_bottom_panel(tab_index=2)),
            ("l", Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK, lambda: self.toggle_bottom_panel(tab_index=2)),

            # Advanced Code Editing
            ("slash", Gdk.ModifierType.CONTROL_MASK, lambda: self._call_editor("toggle_comment")),
            ("d", Gdk.ModifierType.CONTROL_MASK, lambda: self._call_editor("duplicate_line")),
            ("k", Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK, lambda: self._call_editor("delete_line")),
            ("Up", Gdk.ModifierType.MOD1_MASK, lambda: self._call_editor("move_line_up")),
            ("Down", Gdk.ModifierType.MOD1_MASK, lambda: self._call_editor("move_line_down")),
            ("j", Gdk.ModifierType.CONTROL_MASK, lambda: self._call_editor("join_lines")),
            ("u", Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK, lambda: self._call_editor("convert_case", True)),
            ("u", Gdk.ModifierType.CONTROL_MASK, lambda: self._call_editor("convert_case", False)),
            ("bracketright", Gdk.ModifierType.CONTROL_MASK, lambda: self._call_editor("indent_block", True)),
            ("bracketleft", Gdk.ModifierType.CONTROL_MASK, lambda: self._call_editor("indent_block", False)),

            # Find & Navigation
            ("f", Gdk.ModifierType.CONTROL_MASK, lambda: self.on_show_find()),
            ("h", Gdk.ModifierType.CONTROL_MASK, lambda: self.on_show_replace()),
            ("g", Gdk.ModifierType.CONTROL_MASK, lambda: self.on_goto_line()),

            # Zoom
            ("plus", Gdk.ModifierType.CONTROL_MASK, lambda: self.zoom_active(out=False)),
            ("equal", Gdk.ModifierType.CONTROL_MASK, lambda: self.zoom_active(out=False)),
            ("minus", Gdk.ModifierType.CONTROL_MASK, lambda: self.zoom_active(out=True)),
            ("0", Gdk.ModifierType.CONTROL_MASK, lambda: self.zoom_active(reset=True)),

            # Tab cycling
            ("Page_Up", Gdk.ModifierType.CONTROL_MASK, lambda: self._cycle_tab(-1)),
            ("Page_Down", Gdk.ModifierType.CONTROL_MASK, lambda: self._cycle_tab(1)),
        ]

        for key_str, mod, callback in shortcuts:
            keyval = Gdk.keyval_from_name(key_str)
            if keyval != 0:
                accel_group.connect(keyval, mod, Gtk.AccelFlags.VISIBLE, lambda ag, w, kv, m, cb=callback: cb())

    def _cycle_tab(self, delta):
        n = self.notebook_tabs.get_n_pages()
        if n > 1:
            cur = self.notebook_tabs.get_current_page()
            self.notebook_tabs.set_current_page((cur + delta) % n)

    # --------------------------------------------------------------------------
    # Python Execution & Bottom Panel
    # --------------------------------------------------------------------------
    def run_active_script(self, script_args=None):
        """Execute active script in the Script Runner tab using system base interpreter."""
        ed = self.get_current_editor()
        if not ed:
            return

        if not ed.file_path or ed.is_modified():
            if not self.on_save(ed):
                return

        self.toggle_bottom_panel(force_show=True, tab_index=1)
        self.panel.run_script(args=script_args)

    def on_run_with_args(self):
        """Prompt user for command line arguments to pass to the script."""
        ed = self.get_current_editor()
        if not ed:
            return

        dialog = Gtk.Dialog(
            title="Run Module with Arguments",
            transient_for=self,
            flags=Gtk.DialogFlags.MODAL,
            buttons=("Cancel", Gtk.ResponseType.CANCEL, "Run", Gtk.ResponseType.OK)
        )
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_border_width(12)

        safe_name = GLib.markup_escape_text(os.path.basename(ed.file_path or "Script"))
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        lbl = Gtk.Label(label=f"Arguments to pass to <b>{safe_name}</b>:")
        lbl.set_use_markup(True)
        lbl.set_xalign(0)
        entry = Gtk.Entry()
        entry.set_placeholder_text("e.g. --verbose \"input file.csv\" --limit 10")
        entry.set_activates_default(True)

        box.pack_start(lbl, False, False, 0)
        box.pack_start(entry, False, False, 0)
        dialog.get_content_area().add(box)
        dialog.show_all()

        if dialog.run() == Gtk.ResponseType.OK:
            raw_args = entry.get_text().strip()
            if raw_args:
                try:
                    args = shlex.split(raw_args)
                except ValueError:
                    args = raw_args.split()
            else:
                args = []
            dialog.destroy()
            self.run_active_script(script_args=args)
        else:
            dialog.destroy()

    def on_check_syntax(self):
        """Check syntax of the module without running it (Alt+X)."""
        ed = self.get_current_editor()
        if not ed:
            return
        content = ed.get_text()
        diags, _summary, _ = PythonLinter.lint(file_path=ed.file_path, content=content)
        if not diags:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Python Module Syntax OK"
            )
            dialog.format_secondary_text(f"No syntax errors detected in {os.path.basename(ed.file_path or 'document')}.")
            dialog.run()
            dialog.destroy()
        else:
            self.toggle_bottom_panel(force_show=True, tab_index=2)

    def toggle_bottom_panel(self, force_show=None, tab_index=0):
        tab_names = {0: "shell", 1: "console", 2: "lint"}
        target_name = tab_names.get(tab_index, "shell")
        current_name = self.panel.notebook.get_visible_child_name()

        if force_show is None:
            if not self.panel.get_visible():
                show = True
            elif current_name != target_name:
                # Panel is open on another tab: switch to the requested tab instead of hiding
                show = True
            else:
                show = False
        else:
            show = force_show

        was_visible = self.panel.get_visible()
        self.panel.set_visible(show)
        if show:
            if not was_visible:
                win_h = self.get_allocated_height() or self.get_size()[1]
                self.paned.set_position(max(200, win_h - 260))
            self.panel.select_tab(tab_index)
            if tab_index == 2:
                self.panel.run_lint()

    def on_select_interpreter(self):
        """Dialog to select system base or virtualenv Python interpreter."""
        dialog = Gtk.Dialog(
            title="Select Python Interpreter",
            transient_for=self,
            flags=Gtk.DialogFlags.MODAL,
            buttons=("Cancel", Gtk.ResponseType.CANCEL, "Apply", Gtk.ResponseType.OK)
        )
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_border_width(12)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        lbl = Gtk.Label(label="Choose Python interpreter for execution and interactive shell:")
        lbl.set_xalign(0)
        box.pack_start(lbl, False, False, 0)

        combo = Gtk.ComboBoxText()
        interps = InterpreterManager.detect_system_interpreters()
        active = InterpreterManager.get_active_interpreter()
        sel_idx = 0
        for i, (path, ver) in enumerate(interps):
            combo.append_text(f"{ver} — {path}")
            if os.path.realpath(os.path.expanduser(path)) == os.path.realpath(active):
                sel_idx = i
        combo.set_active(sel_idx)
        box.pack_start(combo, False, False, 0)

        entry_custom = Gtk.Entry()
        entry_custom.set_placeholder_text("Or enter custom path to python binary (e.g. /venv/bin/python)...")
        box.pack_start(entry_custom, False, False, 0)

        dialog.get_content_area().add(box)
        dialog.show_all()

        if dialog.run() == Gtk.ResponseType.OK:
            custom = entry_custom.get_text().strip()
            if custom:
                if not InterpreterManager.set_active_interpreter(custom):
                    dialog.destroy()
                    self._show_error(f"Invalid or non-executable Python interpreter path:\n{custom}")
                    return
            else:
                idx = combo.get_active()
                if 0 <= idx < len(interps):
                    InterpreterManager.set_active_interpreter(interps[idx][0])

            ver = InterpreterManager.get_interpreter_version()
            active_path = InterpreterManager.get_active_interpreter()
            self.lbl_interp.set_text(f"Python: {ver} (Base)")
            self.panel.lbl_status.set_text(f"Base Interpreter: {active_path}")
            self.panel.shell_session.banner = (
                f"PythonPad Interactive Shell\n"
                f"Interpreter: {active_path} ({ver})\n"
                f"Type Python expressions below. Use Up/Down arrows for command history.\n"
            )
        dialog.destroy()

    # --------------------------------------------------------------------------
    # Editor Signals & Title Updates (Debounced for Zero-Lag Typing)
    # --------------------------------------------------------------------------
    def _on_cursor_moved(self, editor, line, col):
        if editor == self.get_current_editor():
            self.lbl_pos.set_text(f"Ln {line}, Col {col}")

    def _on_content_modified(self, editor, is_modified):
        self._update_tab_label(editor)
        if editor == self.get_current_editor():
            self.update_title()
            self._schedule_stats_update(editor, immediate=False)

    def _schedule_stats_update(self, editor, immediate=False):
        if self._stats_timeout_id is not None:
            GLib.source_remove(self._stats_timeout_id)
            self._stats_timeout_id = None

        if immediate:
            if editor == self.get_current_editor():
                stats = editor.get_document_statistics()
                self._update_stats_display(stats)
            return

        def _deferred():
            self._stats_timeout_id = None
            cur = self.get_current_editor()
            if cur:
                stats = cur.get_document_statistics()
                self._update_stats_display(stats)
            return False

        self._stats_timeout_id = GLib.timeout_add(120, _deferred)

    def _on_zoom_changed(self, editor, percent):
        if editor == self.get_current_editor():
            self.btn_zoom_reset.set_label(f"{percent}%")
            self.lbl_zoom.set_text(f"Retina: {percent}%")

    def _on_file_saved(self, editor, path):
        self._update_tab_label(editor)
        if editor == self.get_current_editor():
            self.update_title()
            self.lbl_encoding.set_text(f"{editor.file_encoding} | {editor.line_ending}")
            if self.panel.get_visible() and self.panel.tab_btn_lint.get_active():
                self.panel.run_lint()

    def _update_tab_label(self, editor):
        page_num = self.notebook_tabs.page_num(editor)
        if page_num != -1:
            tab_widget = self.notebook_tabs.get_tab_label(editor)
            if isinstance(tab_widget, Gtk.Box):
                children = tab_widget.get_children()
                if children and isinstance(children[0], Gtk.Label):
                    base_name = os.path.basename(editor.file_path) if editor.file_path else "Untitled"
                    mod = "● " if editor.is_modified() else ""
                    new_lbl = f"{mod}{base_name}"
                    if children[0].get_text() != new_lbl:
                        children[0].set_text(new_lbl)

    def update_title(self):
        ed = self.get_current_editor()
        if not ed:
            self.set_title(self.APP_NAME)
            self.header.set_subtitle("")
            return

        base_name = os.path.basename(ed.file_path) if ed.file_path else "Untitled"
        mod = "● " if ed.is_modified() else ""
        self.set_title(f"{mod}{base_name} - {self.APP_NAME}")
        self.header.set_subtitle(f"{mod}{base_name}")

    def _update_stats_display(self, stats):
        self.lbl_stats.set_text(f"{stats['total_lines']} lines, {stats['word_count']} words, {stats['char_count']} chars")

    # --------------------------------------------------------------------------
    # File Operations
    # --------------------------------------------------------------------------
    def on_open(self):
        dialog = Gtk.FileChooserNative.new("Open File", self, Gtk.FileChooserAction.OPEN, "_Open", "_Cancel")
        self._add_file_filters(dialog)
        if dialog.run() == Gtk.ResponseType.ACCEPT:
            path = dialog.get_filename()
            if path:
                self.new_tab(path)
        dialog.destroy()

    def on_save(self, target_editor=None):
        ed = target_editor or self.get_current_editor()
        if not ed:
            return False
        if not ed.file_path:
            return self.on_save_as(ed)
        try:
            ed.save_file()
            return True
        except Exception as e:
            self._show_error(f"Could not save file:\n{e}")
            return False

    def on_save_as(self, target_editor=None):
        ed = target_editor or self.get_current_editor()
        if not ed:
            return False

        dialog = Gtk.FileChooserNative.new("Save As", self, Gtk.FileChooserAction.SAVE, "_Save", "_Cancel")
        dialog.set_do_overwrite_confirmation(True)
        if ed.file_path:
            dialog.set_filename(ed.file_path)
        else:
            dialog.set_current_name("script.py")
        self._add_file_filters(dialog)

        success = False
        if dialog.run() == Gtk.ResponseType.ACCEPT:
            path = dialog.get_filename()
            if path:
                try:
                    ed.save_file(path)
                    success = True
                except Exception as e:
                    self._show_error(f"Could not save file:\n{e}")
        dialog.destroy()
        return success

    def _add_file_filters(self, dialog):
        f_py = Gtk.FileFilter()
        f_py.set_name("Python Files (*.py, *.pyw)")
        f_py.add_pattern("*.py")
        f_py.add_pattern("*.pyw")
        dialog.add_filter(f_py)

        f_text = Gtk.FileFilter()
        f_text.set_name("Text & Code (*.txt, *.md, *.json, *.sh)")
        f_text.add_pattern("*.txt")
        f_text.add_pattern("*.md")
        f_text.add_pattern("*.json")
        f_text.add_pattern("*.sh")
        dialog.add_filter(f_text)

        f_all = Gtk.FileFilter()
        f_all.set_name("All Files")
        f_all.add_pattern("*")
        dialog.add_filter(f_all)

    # --------------------------------------------------------------------------
    # Find, Zoom & View Tools
    # --------------------------------------------------------------------------
    def on_show_find(self):
        ed = self.get_current_editor()
        if ed:
            self.search_bar.set_editor(ed)
            self.search_bar.show_find()

    def on_show_replace(self):
        ed = self.get_current_editor()
        if ed:
            self.search_bar.set_editor(ed)
            self.search_bar.show_replace()

    def zoom_active(self, out=False, reset=False):
        ed = self.get_current_editor()
        if not ed:
            return
        if reset:
            ed.reset_zoom()
        elif out:
            ed.zoom_out()
        else:
            ed.zoom_in()

    def _on_toggle_line_numbers(self, btn):
        show = btn.get_active()
        for i in range(self.notebook_tabs.get_n_pages()):
            self.notebook_tabs.get_nth_page(i).set_show_line_numbers(show)

    def _set_all_word_wrap(self, wrap):
        for i in range(self.notebook_tabs.get_n_pages()):
            self.notebook_tabs.get_nth_page(i).set_word_wrap(wrap)

    def _on_theme_selected(self, radio_item, scheme_id):
        if radio_item.get_active():
            self.current_theme = scheme_id
            if hasattr(self, 'notebook_tabs'):
                for i in range(self.notebook_tabs.get_n_pages()):
                    self.notebook_tabs.get_nth_page(i).set_theme(scheme_id)

    def on_goto_line(self):
        ed = self.get_current_editor()
        if not ed:
            return
        dialog = Gtk.Dialog(title="Go to Line", transient_for=self, flags=Gtk.DialogFlags.MODAL, buttons=("Cancel", Gtk.ResponseType.CANCEL, "Go", Gtk.ResponseType.OK))
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_border_width(10)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label="Line:")
        entry = Gtk.SpinButton.new_with_range(1, max(1, ed.source_buffer.get_line_count()), 1)
        line, _ = ed.get_cursor_position()
        entry.set_value(line)
        entry.set_activates_default(True)
        box.pack_start(lbl, False, False, 0)
        box.pack_start(entry, True, True, 0)
        dialog.get_content_area().add(box)
        dialog.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            ed.goto_line(int(entry.get_value()))
        dialog.destroy()

    def on_choose_font(self):
        ed = self.get_current_editor()
        if not ed:
            return
        dialog = Gtk.FontChooserDialog(title="Select Retina Font", transient_for=self)
        dialog.set_font(f"{ed.base_font_family} {ed.base_font_size}")
        if dialog.run() == Gtk.ResponseType.OK:
            desc = dialog.get_font_desc()
            fam = desc.get_family()
            sz = desc.get_size() // Pango.SCALE
            for i in range(self.notebook_tabs.get_n_pages()):
                self.notebook_tabs.get_nth_page(i).set_font_family_and_size(fam, sz)
        dialog.destroy()

    def on_retina_info(self):
        window = self.get_window()
        scale = window.get_scale_factor() if window else 1
        ed = self.get_current_editor()
        zoom = ed.get_zoom_percent() if ed else 100
        interp = GLib.markup_escape_text(InterpreterManager.get_active_interpreter())
        ver = GLib.markup_escape_text(InterpreterManager.get_interpreter_version())

        text = (
            f"<b>PythonPad Environment Diagnostics:</b>\n\n"
            f"• <b>Base Python:</b> {interp} ({ver})\n"
            f"• <b>Hardware Display Scale:</b> {scale}x ({'HiDPI / Retina Active' if scale > 1 else 'Standard DPI'})\n"
            f"• <b>Current Editor Zoom:</b> {zoom}%\n"
            f"• <b>Subpixel Antialiasing:</b> Cairo RGBA Subpixel Enabled\n\n"
            f"<i>Features:</i>\n"
            f"• Interactive Python REPL Console + F5 Script Runner\n"
            f"• Advanced Code Editing (Multi-tab, comments, line duplication, line shift)\n"
            f"• Pylint &amp; AST Diagnostics Viewer\n"
        )
        dialog = Gtk.MessageDialog(transient_for=self, flags=0, message_type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.OK, text="PythonPad Diagnostics")
        dialog.set_markup(text)
        dialog.run()
        dialog.destroy()

    def on_about(self):
        dialog = Gtk.AboutDialog(transient_for=self)
        dialog.set_program_name(self.APP_NAME)
        dialog.set_version(self.APP_VERSION)
        dialog.set_comments(
            "A fast, modern Python IDE and code editor with Retina Vision, "
            "line numbers, interactive Python shell, advanced editing operations, "
            "and system base interpreter script execution for Linux Mint Cinnamon."
        )
        dialog.set_website("https://github.com/kyledeanml/pythonpad")
        dialog.set_website_label("PythonPad on GitHub")
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pythonpad.svg")
        if os.path.exists(icon_path):
            try:
                dialog.set_logo(GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_path, 96, 96, True))
            except Exception:
                pass
        dialog.run()
        dialog.destroy()

    def _show_error(self, msg):
        dialog = Gtk.MessageDialog(transient_for=self, flags=0, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK, text="PythonPad Error")
        dialog.format_secondary_text(str(msg))
        dialog.run()
        dialog.destroy()

    def _on_delete_event(self, widget, event):
        # Check all tabs for unsaved changes
        for i in range(self.notebook_tabs.get_n_pages()):
            ed = self.notebook_tabs.get_nth_page(i)
            if ed.is_modified():
                self.notebook_tabs.set_current_page(i)
                fname = os.path.basename(ed.file_path) if ed.file_path else "Untitled"
                dialog = Gtk.MessageDialog(
                    transient_for=self,
                    flags=0,
                    message_type=Gtk.MessageType.WARNING,
                    buttons=Gtk.ButtonsType.NONE,
                    text=f"Save changes to \"{fname}\" before quitting?"
                )
                dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
                dialog.add_button("Discard", Gtk.ResponseType.NO)
                dialog.add_button("Save", Gtk.ResponseType.YES)
                resp = dialog.run()
                dialog.destroy()

                if resp == Gtk.ResponseType.YES:
                    if not self.on_save(ed):
                        return True
                elif resp != Gtk.ResponseType.NO:
                    return True

        # Stop any active background script runner before quitting
        if hasattr(self, 'panel') and self.panel.runner.is_running:
            self.panel.runner.stop()
        return False


class PythonPadApp(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="org.linuxmint.pythonpad",
            flags=Gio.ApplicationFlags.HANDLES_OPEN | Gio.ApplicationFlags.NON_UNIQUE
        )
        self.files_to_open = []

    def do_activate(self):
        win = PythonPadWindow(self, initial_files=self.files_to_open)
        win.present()

    def do_open(self, files, n_files, hint):
        paths = [f.get_path() for f in files if f.get_path()]
        win = PythonPadWindow(self, initial_files=paths)
        win.present()


def main():
    GLib.set_prgname("pythonpad")
    GLib.set_application_name("PythonPad")
    app = PythonPadApp()
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        app.files_to_open = [os.path.abspath(f) for f in sys.argv[1:]]
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
