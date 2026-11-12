#!/usr/bin/env python3
"""
PythonPanel - Bottom Workspace Panel
Provides:
  1. Interactive Python Shell (REPL with persistent session and history)
  2. Script Runner Console (executing with system base interpreter + interactive stdin)
  3. Pylint & Diagnostics Viewer (error/warning inspection with click-to-jump)
"""

import os
import threading
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Pango', '1.0')

from gi.repository import Gtk, Gdk, Pango, GLib, GObject
from python_tools import (
    PythonLinter,
    PythonRunner,
    InteractiveShellSession,
    InterpreterManager,
    Diagnostic
)


class PythonWorkspacePanel(Gtk.Box):
    """
    Bottom docked workspace panel housing:
    - Interactive Python Shell
    - Python Script Runner Console
    - Pylint & Code Diagnostics Viewer
    """

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
        self.shell_session = InteractiveShellSession(input_handler=self._prompt_shell_input)
        self.history = []
        self.history_idx = -1
        self.is_continuation = False
        self._lint_generation = 0

        # Batched console output queue to prevent UI freezes on high-speed stdout
        self._console_lock = threading.Lock()
        self._console_queue = []
        self._console_flush_scheduled = False

        self.set_size_request(-1, 240)
        self._build_ui()
        self._init_shell_banner()

    def _build_ui(self):
        # Header / Tab Bar
        tab_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        tab_bar.get_style_context().add_class("bottom-panel-bar")
        tab_bar.set_margin_start(8)
        tab_bar.set_margin_end(8)
        tab_bar.set_margin_top(4)
        tab_bar.set_margin_bottom(4)

        # Tab switch buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        Gtk.StyleContext.add_class(btn_box.get_style_context(), "linked")

        self.tab_btn_shell = Gtk.RadioButton.new_with_label(None, "Python Shell")
        self.tab_btn_shell.set_mode(False)
        self.tab_btn_shell.connect("toggled", lambda b: self._switch_tab(0) if b.get_active() else None)
        btn_box.pack_start(self.tab_btn_shell, False, False, 0)

        self.tab_btn_run = Gtk.RadioButton.new_with_label_from_widget(self.tab_btn_shell, "Script Runner")
        self.tab_btn_run.set_mode(False)
        self.tab_btn_run.connect("toggled", lambda b: self._switch_tab(1) if b.get_active() else None)
        btn_box.pack_start(self.tab_btn_run, False, False, 0)

        self.tab_btn_lint = Gtk.RadioButton.new_with_label_from_widget(self.tab_btn_shell, "Pylint Diagnostics")
        self.tab_btn_lint.set_mode(False)
        self.tab_btn_lint.connect("toggled", self._on_lint_tab_toggled)
        btn_box.pack_start(self.tab_btn_lint, False, False, 0)

        tab_bar.pack_start(btn_box, False, False, 0)

        # Status text
        self.lbl_status = Gtk.Label(label="Base Interpreter: " + InterpreterManager.get_active_interpreter())
        self.lbl_status.set_xalign(0)
        self.lbl_status.set_ellipsize(Pango.EllipsizeMode.END)
        self.lbl_status.set_margin_start(12)
        tab_bar.pack_start(self.lbl_status, True, True, 0)

        # Controls for Shell
        self.btn_shell_restart = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        self.btn_shell_restart.set_tooltip_text("Restart Shell / Reset Environment (Ctrl+F6)")
        self.btn_shell_restart.connect("clicked", lambda b: self.restart_shell())
        tab_bar.pack_end(self._create_close_btn(), False, False, 0)
        tab_bar.pack_end(self.btn_shell_restart, False, False, 0)

        # Controls for Linter
        self.btn_lint_refresh = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        self.btn_lint_refresh.set_tooltip_text("Re-run Pylint Diagnostics (F8)")
        self.btn_lint_refresh.connect("clicked", lambda b: self.run_lint())
        tab_bar.pack_end(self.btn_lint_refresh, False, False, 0)

        # Controls for Script Runner
        self.btn_run_script = Gtk.Button.new_from_icon_name("media-playback-start-symbolic", Gtk.IconSize.BUTTON)
        self.btn_run_script.set_tooltip_text("Run Active Script (F5)")
        self.btn_run_script.connect("clicked", lambda b: self.run_script())
        tab_bar.pack_end(self.btn_run_script, False, False, 0)

        self.btn_stop_script = Gtk.Button.new_from_icon_name("media-playback-stop-symbolic", Gtk.IconSize.BUTTON)
        self.btn_stop_script.set_tooltip_text("Stop Running Script")
        self.btn_stop_script.set_sensitive(False)
        self.btn_stop_script.connect("clicked", lambda b: self.runner.stop())
        tab_bar.pack_end(self.btn_stop_script, False, False, 0)

        self.btn_clear_output = Gtk.Button.new_from_icon_name("edit-clear-symbolic", Gtk.IconSize.BUTTON)
        self.btn_clear_output.set_tooltip_text("Clear View")
        self.btn_clear_output.connect("clicked", lambda b: self._clear_active_view())
        tab_bar.pack_end(self.btn_clear_output, False, False, 0)

        self.pack_start(tab_bar, False, False, 0)

        # Stack container
        self.notebook = Gtk.Stack()
        self.notebook.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.notebook.set_transition_duration(100)

        self._build_shell_view()
        self._build_console_view()
        self._build_lint_view()

        self.pack_start(self.notebook, True, True, 0)

        # Make all internal child widgets visible before hiding non-active tab buttons
        self.show_all()
        self._switch_tab(0)

    def _create_close_btn(self):
        btn = Gtk.Button.new_from_icon_name("window-close-symbolic", Gtk.IconSize.BUTTON)
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.set_tooltip_text("Hide Panel")
        btn.connect("clicked", lambda b: self.emit("close-requested"))
        return btn

    def _on_lint_tab_toggled(self, btn):
        if btn.get_active():
            self._switch_tab(2)
            if not getattr(self, "_in_run_lint", False):
                self.run_lint()

    def select_tab(self, index: int):
        """Programmatically select a panel tab (0=Shell, 1=Runner, 2=Lint) and sync UI."""
        if index == 0:
            self.tab_btn_shell.set_active(True)
        elif index == 1:
            self.tab_btn_run.set_active(True)
        else:
            self.tab_btn_lint.set_active(True)
        self._switch_tab(index)

    def _switch_tab(self, index):
        if index == 0:
            self.notebook.set_visible_child_name("shell")
            self.btn_shell_restart.set_visible(True)
            self.btn_lint_refresh.set_visible(False)
            self.btn_run_script.set_visible(False)
            self.btn_stop_script.set_visible(False)
            self.btn_clear_output.set_visible(True)
            self.shell_entry.grab_focus()
        elif index == 1:
            self.notebook.set_visible_child_name("console")
            self.btn_shell_restart.set_visible(False)
            self.btn_lint_refresh.set_visible(False)
            self.btn_run_script.set_visible(True)
            self.btn_stop_script.set_visible(True)
            self.btn_clear_output.set_visible(True)
        else:
            self.notebook.set_visible_child_name("lint")
            self.btn_shell_restart.set_visible(False)
            self.btn_lint_refresh.set_visible(True)
            self.btn_run_script.set_visible(False)
            self.btn_stop_script.set_visible(False)
            self.btn_clear_output.set_visible(False)

    def _clear_active_view(self):
        active = self.notebook.get_visible_child_name()
        if active == "shell":
            self.shell_buffer.set_text("")
            self._init_shell_banner()
        elif active == "console":
            self.console_buffer.set_text("")

    # --------------------------------------------------------------------------
    # 1. Interactive Shell View
    # --------------------------------------------------------------------------
    def _build_shell_view(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Output text view
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.shell_buffer = Gtk.TextBuffer()
        self._shell_end_mark = self.shell_buffer.create_mark(
            "shell_end", self.shell_buffer.get_end_iter(), False
        )
        self.shell_view = Gtk.TextView(buffer=self.shell_buffer)
        self.shell_view.set_editable(False)
        self.shell_view.set_cursor_visible(False)
        self.shell_view.set_monospace(True)
        self.shell_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.shell_view.set_left_margin(10)
        self.shell_view.set_right_margin(10)
        self.shell_view.set_top_margin(6)
        self.shell_view.set_bottom_margin(6)

        # Shell color tags (Dark mode with white and neon blue hues)
        self.tag_prompt = self.shell_buffer.create_tag("prompt", foreground="#00f0ff", weight=Pango.Weight.BOLD)
        self.tag_input = self.shell_buffer.create_tag("input", foreground="#ffffff", weight=Pango.Weight.BOLD)
        self.tag_out = self.shell_buffer.create_tag("output", foreground="#e0f2fe")
        self.tag_err = self.shell_buffer.create_tag("error", foreground="#f43f5e")
        self.tag_banner = self.shell_buffer.create_tag("banner", foreground="#38bdf8", style=Pango.Style.ITALIC)

        scrolled.add(self.shell_view)
        box.pack_start(scrolled, True, True, 0)

        # Shell Input Bar (>>> entry)
        entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        entry_box.set_margin_start(8)
        entry_box.set_margin_end(8)
        entry_box.set_margin_top(4)
        entry_box.set_margin_bottom(4)

        self.lbl_prompt = Gtk.Label(label=">>> ")
        self.lbl_prompt.get_style_context().add_class("shell-prompt")
        entry_box.pack_start(self.lbl_prompt, False, False, 0)

        self.shell_entry = Gtk.Entry()
        self.shell_entry.set_placeholder_text("Type Python expression or code and press Enter...")
        self.shell_entry.connect("activate", self._on_shell_submit)
        self.shell_entry.connect("key-press-event", self._on_shell_key_press)
        entry_box.pack_start(self.shell_entry, True, True, 0)

        btn_exec = Gtk.Button(label="Execute")
        btn_exec.set_tooltip_text("Execute Python command in shell")
        btn_exec.connect("clicked", lambda b: self._on_shell_submit(self.shell_entry))
        entry_box.pack_start(btn_exec, False, False, 0)

        box.pack_start(entry_box, False, False, 0)
        self.notebook.add_named(box, "shell")

    def _prompt_shell_input(self, prompt_text=""):
        """Show a modal dialog if user code in the interactive shell calls input()."""
        toplevel = self.get_toplevel()
        parent = toplevel if isinstance(toplevel, Gtk.Window) else None
        dialog = Gtk.Dialog(
            title="Python Shell Input",
            transient_for=parent,
            flags=Gtk.DialogFlags.MODAL,
            buttons=("Cancel", Gtk.ResponseType.CANCEL, "Submit", Gtk.ResponseType.OK)
        )
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_border_width(10)

        content = dialog.get_content_area()
        content.set_spacing(6)
        lbl = Gtk.Label(label=prompt_text or "Enter input:")
        lbl.set_xalign(0)
        entry = Gtk.Entry()
        entry.set_activates_default(True)
        content.pack_start(lbl, False, False, 0)
        content.pack_start(entry, False, False, 0)
        dialog.show_all()

        resp = dialog.run()
        val = entry.get_text() if resp == Gtk.ResponseType.OK else None
        dialog.destroy()
        return val

    def _init_shell_banner(self):
        buf = self.shell_buffer
        end = buf.get_end_iter()
        tag = buf.get_tag_table().lookup("banner")
        buf.insert_with_tags(end, self.shell_session.banner + "\n", tag)

    def _on_shell_submit(self, entry):
        line = entry.get_text()
        entry.set_text("")
        prompt = "... " if self.is_continuation else ">>> "

        # Sync working directory to current editor's directory if available
        editor = self.editor_getter()
        if editor and editor.file_path:
            ed_dir = os.path.dirname(os.path.abspath(editor.file_path))
            if os.path.isdir(ed_dir):
                try:
                    os.chdir(ed_dir)
                except OSError:
                    pass

        # Append submitted command to buffer
        buf = self.shell_buffer
        end = buf.get_end_iter()
        tag_p = buf.get_tag_table().lookup("prompt")
        tag_i = buf.get_tag_table().lookup("input")
        buf.insert_with_tags(end, prompt, tag_p)
        buf.insert_with_tags(buf.get_end_iter(), line + "\n", tag_i)

        if line.strip():
            self.history.append(line)
        self.history_idx = len(self.history)

        output, more = self.shell_session.push_line(line)
        self.is_continuation = more
        self.lbl_prompt.set_text("... " if more else ">>> ")

        if output:
            end = buf.get_end_iter()
            is_err = "Traceback (most recent call last):" in output or "SyntaxError:" in output
            tag_o = buf.get_tag_table().lookup("error" if is_err else "output")
            buf.insert_with_tags(end, output, tag_o)

        # Scroll to bottom using persistent mark
        buf.move_mark(self._shell_end_mark, buf.get_end_iter())
        self.shell_view.scroll_to_mark(self._shell_end_mark, 0.05, False, 0.0, 0.0)

    def _on_shell_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Up:
            if self.history and self.history_idx > 0:
                self.history_idx -= 1
                self.shell_entry.set_text(self.history[self.history_idx])
                self.shell_entry.set_position(-1)
                return True
        elif event.keyval == Gdk.KEY_Down:
            if self.history and self.history_idx < len(self.history) - 1:
                self.history_idx += 1
                self.shell_entry.set_text(self.history[self.history_idx])
                self.shell_entry.set_position(-1)
                return True
            elif self.history_idx >= len(self.history) - 1:
                self.history_idx = len(self.history)
                self.shell_entry.set_text("")
                return True
        return False

    def restart_shell(self):
        msg = self.shell_session.restart()
        self.is_continuation = False
        self.lbl_prompt.set_text(">>> ")
        buf = self.shell_buffer
        end = buf.get_end_iter()
        tag_b = buf.get_tag_table().lookup("banner")
        buf.insert_with_tags(end, f"\n{msg}\n", tag_b)
        buf.move_mark(self._shell_end_mark, buf.get_end_iter())
        self.shell_view.scroll_to_mark(self._shell_end_mark, 0.05, False, 0.0, 0.0)
        self.shell_entry.grab_focus()

    # --------------------------------------------------------------------------
    # 2. Script Runner View (Base Interpreter + Interactive Stdin)
    # --------------------------------------------------------------------------
    def _build_console_view(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.console_buffer = Gtk.TextBuffer()
        self._console_end_mark = self.console_buffer.create_mark(
            "console_end", self.console_buffer.get_end_iter(), False
        )
        self.console_view = Gtk.TextView(buffer=self.console_buffer)
        self.console_view.set_editable(False)
        self.console_view.set_cursor_visible(False)
        self.console_view.set_monospace(True)
        self.console_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.console_view.set_left_margin(10)
        self.console_view.set_right_margin(10)
        self.console_view.set_top_margin(8)
        self.console_view.set_bottom_margin(8)

        self.tag_stdout = self.console_buffer.create_tag("stdout", foreground="#f8fafc")
        self.tag_stderr = self.console_buffer.create_tag("stderr", foreground="#f43f5e")
        self.tag_system = self.console_buffer.create_tag("system", foreground="#00f0ff", weight=Pango.Weight.BOLD)
        self.tag_success = self.console_buffer.create_tag("success", foreground="#22d3ee", weight=Pango.Weight.BOLD)

        scrolled.add(self.console_view)
        box.pack_start(scrolled, True, True, 0)

        # Interactive Stdin Bar for running scripts (e.g. input() prompts)
        stdin_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        stdin_box.set_margin_start(8)
        stdin_box.set_margin_end(8)
        stdin_box.set_margin_top(4)
        stdin_box.set_margin_bottom(4)

        lbl_stdin = Gtk.Label(label="stdin:")
        lbl_stdin.get_style_context().add_class("shell-prompt")
        stdin_box.pack_start(lbl_stdin, False, False, 0)

        self.console_entry = Gtk.Entry()
        self.console_entry.set_placeholder_text("Send input to running script (press Enter)...")
        self.console_entry.connect("activate", self._on_console_stdin_submit)
        stdin_box.pack_start(self.console_entry, True, True, 0)

        btn_send = Gtk.Button(label="Send")
        btn_send.connect("clicked", lambda b: self._on_console_stdin_submit(self.console_entry))
        stdin_box.pack_start(btn_send, False, False, 0)

        box.pack_start(stdin_box, False, False, 0)
        self.notebook.add_named(box, "console")

    def _on_console_stdin_submit(self, entry):
        text = entry.get_text()
        if self.runner.is_running:
            entry.set_text("")
            self._append_console(text + "\n", "system")
            self.runner.send_input(text)

    def run_script(self, args=None):
        """Execute active file with system base interpreter."""
        editor = self.editor_getter()
        if not editor:
            return

        if not editor.file_path or editor.is_modified():
            self.lbl_status.set_text("Please save file before running.")
            return

        if self.runner.is_running:
            self.runner.stop()

        self.select_tab(1)

        interp = InterpreterManager.get_active_interpreter()
        ver = InterpreterManager.get_interpreter_version()
        fname = os.path.basename(editor.file_path)

        with self._console_lock:
            self._console_queue.clear()

        self.console_buffer.set_text("")
        self._append_console(f"▶ Running script with {interp} ({ver})\n", "system")
        self._append_console(f"▶ File: {editor.file_path}\n" + ("-" * 60) + "\n\n", "system")

        self.btn_run_script.set_sensitive(False)
        self.btn_stop_script.set_sensitive(True)
        self.lbl_status.set_text(f"Running script ({fname})...")
        self.console_entry.grab_focus()

        def _on_output(text, is_stderr):
            tag = "stderr" if is_stderr else "stdout"
            with self._console_lock:
                self._console_queue.append((text, tag))
                if not self._console_flush_scheduled:
                    self._console_flush_scheduled = True
                    GLib.idle_add(self._flush_console_queue)

        def _on_finished(rc):
            def _ui_finish():
                self._flush_console_queue()
                tag = "success" if rc == 0 else "stderr"
                self._append_console(f"\n" + ("-" * 60) + f"\n■ Process finished with exit code {rc}\n", tag)
                self.btn_run_script.set_sensitive(True)
                self.btn_stop_script.set_sensitive(False)
                self.lbl_status.set_text(f"Finished {fname} (exit code {rc})")
                return False
            GLib.idle_add(_ui_finish)

        def _start_when_ready(attempt=0):
            if self.runner.is_running and attempt < 20:
                GLib.timeout_add(30, _start_when_ready, attempt + 1)
                return False
            self.runner.run(editor.file_path, _on_output, _on_finished, script_args=args, custom_interpreter=interp)
            return False

        _start_when_ready()

    def _flush_console_queue(self):
        with self._console_lock:
            items = list(self._console_queue)
            self._console_queue.clear()
            self._console_flush_scheduled = False

        if not items:
            return False

        buf = self.console_buffer
        tag_table = buf.get_tag_table()
        for text, tag_name in items:
            end = buf.get_end_iter()
            if tag_name:
                tag = tag_table.lookup(tag_name)
                buf.insert_with_tags(end, text, tag)
            else:
                buf.insert(end, text)

        buf.move_mark(self._console_end_mark, buf.get_end_iter())
        self.console_view.scroll_to_mark(self._console_end_mark, 0.05, False, 0.0, 0.0)
        return False

    def _append_console(self, text, tag_name=None):
        buf = self.console_buffer
        end = buf.get_end_iter()
        if tag_name:
            tag = buf.get_tag_table().lookup(tag_name)
            buf.insert_with_tags(end, text, tag)
        else:
            buf.insert(end, text)

        buf.move_mark(self._console_end_mark, buf.get_end_iter())
        self.console_view.scroll_to_mark(self._console_end_mark, 0.05, False, 0.0, 0.0)
        return False

    # --------------------------------------------------------------------------
    # 3. Pylint Diagnostics View
    # --------------------------------------------------------------------------
    def _build_lint_view(self):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.lint_store = Gtk.ListStore(str, str, int, int, str, str)
        self.tree_view = Gtk.TreeView(model=self.lint_store)
        self.tree_view.set_headers_visible(True)

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

        col_line = Gtk.TreeViewColumn("Line", Gtk.CellRendererText(), text=self.COL_LINE)
        col_line.set_min_width(55)
        col_line.set_resizable(True)
        self.tree_view.append_column(col_line)

        col_col = Gtk.TreeViewColumn("Col", Gtk.CellRendererText(), text=self.COL_COL)
        col_col.set_min_width(50)
        col_col.set_resizable(True)
        self.tree_view.append_column(col_col)

        col_code = Gtk.TreeViewColumn("Code", Gtk.CellRendererText(), text=self.COL_CODE)
        col_code.set_min_width(70)
        col_code.set_resizable(True)
        self.tree_view.append_column(col_code)

        col_msg = Gtk.TreeViewColumn("Message", Gtk.CellRendererText(), text=self.COL_MESSAGE)
        col_msg.set_resizable(True)
        self.tree_view.append_column(col_msg)

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
        editor = self.editor_getter()
        if not editor:
            return

        self._in_run_lint = True
        try:
            self.select_tab(2)
        finally:
            self._in_run_lint = False

        content = editor.get_text()
        file_path = editor.file_path

        self._lint_generation += 1
        current_gen = self._lint_generation

        self.lint_store.clear()
        self.lbl_status.set_text("Analyzing Python code with Pylint/AST...")

        def _lint_async():
            diags, summary, used_pylint = PythonLinter.lint(file_path=file_path, content=content)
            GLib.idle_add(self._apply_lint_results, current_gen, diags, summary, used_pylint)

        threading.Thread(target=_lint_async, daemon=True).start()

    def _apply_lint_results(self, gen, diagnostics, summary, used_pylint):
        if gen != self._lint_generation:
            return False
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
        return False
