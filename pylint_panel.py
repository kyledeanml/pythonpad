#!/usr/bin/env python3
"""
RetinaPad - Pylint Viewer & Python Console Panel
Provides a bottom pane with diagnostics (Pylint / Syntax) and execution output.
"""

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Pango', '1.0')

from gi.repository import Gtk, Gdk, Pango, GLib, GObject
from python_tools import PythonLinter, PythonRunner, Diagnostic


class PylintPanel(Gtk.Box):
    """Bottom docked panel with Pylint Diagnostics viewer and Python Run console."""

    __gsignals__ = {
        'goto-location': (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
        'close-requested': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    COL_SEVERITY_ICON = 0
    COL_SEVERITY_TEXT = 1
    COL_LINE = 2
    COL_COL = 3
    COL_CODE = 4
    COL_MESSAGE = 5

    def __init__(self, editor_getter):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.editor_getter = editor_getter
        self.runner = PythonRunner()

        self.set_size_request(-1, 210)
        self._build_ui()

    def _build_ui(self):
        # Header / Tab Bar
        tab_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        tab_bar.set_margin_start(8)
        tab_bar.set_margin_end(8)
        tab_bar.set_margin_top(4)
        tab_bar.set_margin_bottom(4)

        # Tab switch buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        Gtk.StyleContext.add_class(btn_box.get_style_context(), "linked")

        self.tab_btn_lint = Gtk.RadioButton.new_with_label(None, "Pylint Diagnostics")
        self.tab_btn_lint.set_mode(False)
        self.tab_btn_lint.connect("toggled", lambda b: self._switch_tab(0) if b.get_active() else None)
        btn_box.pack_start(self.tab_btn_lint, False, False, 0)

        self.tab_btn_run = Gtk.RadioButton.new_with_label_from_widget(self.tab_btn_lint, "Python Console")
        self.tab_btn_run.set_mode(False)
        self.tab_btn_run.connect("toggled", lambda b: self._switch_tab(1) if b.get_active() else None)
        btn_box.pack_start(self.tab_btn_run, False, False, 0)

        tab_bar.pack_start(btn_box, False, False, 0)

        # Status text
        self.lbl_status = Gtk.Label(label="Ready")
        self.lbl_status.set_xalign(0)
        self.lbl_status.set_margin_start(12)
        tab_bar.pack_start(self.lbl_status, True, True, 0)

        # Action buttons
        self.btn_action = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        self.btn_action.set_tooltip_text("Refresh Pylint (F8)")
        self.btn_action.connect("clicked", lambda b: self.run_lint())
        tab_bar.pack_end(self._create_close_btn(), False, False, 0)
        tab_bar.pack_end(self.btn_action, False, False, 0)

        # Run / Stop controls for Console
        self.btn_run_script = Gtk.Button.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.BUTTON)
        self.btn_run_script.set_tooltip_text("Run Python Script (F5)")
        self.btn_run_script.connect("clicked", lambda b: self.run_script())
        tab_bar.pack_end(self.btn_run_script, False, False, 0)

        self.btn_stop_script = Gtk.Button.new_from_icon_name("media-playback-stop-symbolic", Gtk.IconSize.BUTTON)
        self.btn_stop_script.set_tooltip_text("Stop Running Script")
        self.btn_stop_script.set_sensitive(False)
        self.btn_stop_script.connect("clicked", lambda b: self.runner.stop())
        tab_bar.pack_end(self.btn_stop_script, False, False, 0)

        self.btn_clear_console = Gtk.Button.new_from_icon_name("edit-clear-symbolic", Gtk.IconSize.BUTTON)
        self.btn_clear_console.set_tooltip_text("Clear Console Output")
        self.btn_clear_console.connect("clicked", lambda b: self.clear_console())
        tab_bar.pack_end(self.btn_clear_console, False, False, 0)

        self.pack_start(tab_bar, False, False, 0)

        # Notebook stack
        self.notebook = Gtk.Stack()
        self.notebook.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.notebook.set_transition_duration(100)

        self._build_lint_view()
        self._build_console_view()

        self.pack_start(self.notebook, True, True, 0)

    def _create_close_btn(self):
        btn = Gtk.Button.new_from_icon_name("window-close-symbolic", Gtk.IconSize.BUTTON)
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.set_tooltip_text("Hide Panel (Esc)")
        btn.connect("clicked", lambda b: self.emit("close-requested"))
        return btn

    def _switch_tab(self, index):
        if index == 0:
            self.notebook.set_visible_child_name("lint")
            self.btn_action.set_visible(True)
            self.btn_run_script.set_visible(False)
            self.btn_stop_script.set_visible(False)
            self.btn_clear_console.set_visible(False)
        else:
            self.notebook.set_visible_child_name("console")
            self.btn_action.set_visible(False)
            self.btn_run_script.set_visible(True)
            self.btn_stop_script.set_visible(True)
            self.btn_clear_console.set_visible(True)

    # --------------------------------------------------------------------------
    # Pylint View
    # --------------------------------------------------------------------------
    def _build_lint_view(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        # Model: [icon_name, severity_str, line_int, col_int, code_str, message_str]
        self.lint_store = Gtk.ListStore(str, str, int, int, str, str)
        self.tree_view = Gtk.TreeView(model=self.lint_store)
        self.tree_view.set_headers_visible(True)

        # Col 1: Severity (Icon + Text)
        col_sev = Gtk.TreeViewColumn("Severity")
        icon_cell = Gtk.CellRendererPixbuf()
        text_cell = Gtk.CellRendererText()
        col_sev.pack_start(icon_cell, False)
        col_sev.pack_start(text_cell, True)
        col_sev.add_attribute(icon_cell, "icon-name", self.COL_SEVERITY_ICON)
        col_sev.add_attribute(text_cell, "text", self.COL_SEVERITY_TEXT)
        col_sev.set_min_width(120)
        col_sev.set_resizable(True)
        self.tree_view.append_column(col_sev)

        # Col 2: Line
        col_line = Gtk.TreeViewColumn("Line", Gtk.CellRendererText(), text=self.COL_LINE)
        col_line.set_min_width(55)
        col_line.set_resizable(True)
        self.tree_view.append_column(col_line)

        # Col 3: Column
        col_col = Gtk.TreeViewColumn("Col", Gtk.CellRendererText(), text=self.COL_COL)
        col_col.set_min_width(50)
        col_col.set_resizable(True)
        self.tree_view.append_column(col_col)

        # Col 4: Code
        col_code = Gtk.TreeViewColumn("Code", Gtk.CellRendererText(), text=self.COL_CODE)
        col_code.set_min_width(70)
        col_code.set_resizable(True)
        self.tree_view.append_column(col_code)

        # Col 5: Message
        col_msg = Gtk.TreeViewColumn("Message", Gtk.CellRendererText(), text=self.COL_MESSAGE)
        col_msg.set_resizable(True)
        self.tree_view.append_column(col_msg)

        # Row activation (double click or Enter)
        self.tree_view.connect("row-activated", self._on_lint_row_activated)

        scrolled.add(self.tree_view)
        self.notebook.add_named(scrolled, "lint")

    def _on_lint_row_activated(self, tree, path, column):
        model = tree.get_model()
        iter_ = model.get_iter(path)
        if iter_:
            line = model.get_value(iter_, self.COL_LINE)
            col = model.get_value(iter_, self.COL_COL)
            self.emit("goto-location", line, col)

    def run_lint(self):
        """Executes pylint on current editor content and populates list."""
        editor = self.editor_getter()
        if not editor:
            return

        self.tab_btn_lint.set_active(True)
        self._switch_tab(0)

        content = editor.get_text()
        file_path = editor.file_path

        self.lint_store.clear()
        self.lbl_status.set_text("Analyzing Python code...")

        def _lint_async():
            diags, summary, used_pylint = PythonLinter.lint(file_path=file_path, content=content)
            GLib.idle_add(self._apply_lint_results, diags, summary, used_pylint)

        import threading
        threading.Thread(target=_lint_async, daemon=True).start()

    def _apply_lint_results(self, diagnostics, summary, used_pylint):
        self.lint_store.clear()
        self.lbl_status.set_text(summary)

        icon_map = {
            "error": "dialog-error-symbolic",
            "warning": "dialog-warning-symbolic",
            "refactor": "emblem-synchronizing-symbolic",
            "convention": "dialog-information-symbolic",
        }

        for d in diagnostics:
            icon = icon_map.get(d.severity, "dialog-information-symbolic")
            sev_label = d.severity.capitalize()
            self.lint_store.append([
                icon,
                sev_label,
                d.line,
                d.column,
                d.code,
                f"{d.message} ({d.symbol})" if d.symbol else d.message
            ])

    # --------------------------------------------------------------------------
    # Python Console View
    # --------------------------------------------------------------------------
    def _build_console_view(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.console_buffer = Gtk.TextBuffer()
        self.console_view = Gtk.TextView(buffer=self.console_buffer)
        self.console_view.set_editable(False)
        self.console_view.set_cursor_visible(False)
        self.console_view.set_monospace(True)
        self.console_view.set_left_margin(10)
        self.console_view.set_right_margin(10)
        self.console_view.set_top_margin(8)
        self.console_view.set_bottom_margin(8)

        # Style tags
        self.tag_stdout = self.console_buffer.create_tag("stdout")
        self.tag_stderr = self.console_buffer.create_tag("stderr", foreground="#e74c3c")
        self.tag_system = self.console_buffer.create_tag("system", foreground="#3498db", weight=Pango.Weight.BOLD)
        self.tag_success = self.console_buffer.create_tag("success", foreground="#2ecc71", weight=Pango.Weight.BOLD)

        scrolled.add(self.console_view)
        self.notebook.add_named(scrolled, "console")

    def run_script(self):
        """Executes currently opened file in Python Console."""
        editor = self.editor_getter()
        if not editor:
            return

        # Ensure file is saved before running
        if not editor.file_path or editor.is_modified():
            self.lbl_status.set_text("Please save the file before running.")
            return

        self.tab_btn_run.set_active(True)
        self._switch_tab(1)

        self.clear_console()
        self._append_console(f"▶ Running {editor.file_path} ...\n", "system")
        self.btn_run_script.set_sensitive(False)
        self.btn_stop_script.set_sensitive(True)
        self.lbl_status.set_text("Python script is running...")

        def _on_output(text, is_stderr):
            tag = "stderr" if is_stderr else "stdout"
            GLib.idle_add(self._append_console, text, tag)

        def _on_finished(rc):
            def _ui_finish():
                tag = "success" if rc == 0 else "stderr"
                self._append_console(f"\n■ Process exited with code {rc}\n", tag)
                self.btn_run_script.set_sensitive(True)
                self.btn_stop_script.set_sensitive(False)
                self.lbl_status.set_text(f"Execution finished (code {rc})")
            GLib.idle_add(_ui_finish)

        self.runner.run(editor.file_path, _on_output, _on_finished)

    def _append_console(self, text, tag_name=None):
        buf = self.console_buffer
        end = buf.get_end_iter()
        if tag_name:
            tag = buf.get_tag_table().lookup(tag_name)
            buf.insert_with_tags(end, text, tag)
        else:
            buf.insert(end, text)

        # Auto-scroll to end
        mark = buf.create_mark(None, buf.get_end_iter(), False)
        self.console_view.scroll_to_mark(mark, 0.05, False, 0.0, 0.0)

    def clear_console(self):
        self.console_buffer.set_text("")
