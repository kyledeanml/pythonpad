#!/usr/bin/env python3
"""
Unit and Integration Tests for PythonPad
Tests interactive REPL, system interpreter execution, advanced editing operations,
retina zoom scaling, and desktop asset integrity.
"""

import os
import tempfile
import threading
import unittest
import xml.etree.ElementTree as ET
import gi

gi.require_version('GtkSource', '4')
from gi.repository import GtkSource

from editor import RetinaEditor
from python_tools import (
    PythonLinter,
    PythonRunner,
    Diagnostic,
    InterpreterManager,
    InteractiveShellSession
)


class TestInteractiveShellFeatures(unittest.TestCase):
    """Test persistent interactive shell and interpreter detection."""

    def test_system_base_interpreter(self):
        interp = InterpreterManager.get_active_interpreter()
        self.assertTrue(os.path.exists(interp), f"Base interpreter {interp} not found")
        ver = InterpreterManager.get_interpreter_version()
        self.assertIn("Python", ver)

    def test_interactive_shell_persistence(self):
        session = InteractiveShellSession()
        out, more = session.push_line("x = 100 * 2")
        self.assertFalse(more)

        out, more = session.push_line("print('val:', x)")
        self.assertFalse(more)
        self.assertIn("val: 200", out)

    def test_interactive_shell_restart(self):
        session = InteractiveShellSession()
        session.push_line("secret_var = 'stored'")
        msg = session.restart()
        self.assertIn("Clean", msg)
        out, more = session.push_line("print(secret_var)")
        self.assertIn("NameError", out)

    def test_interactive_shell_exit_and_interrupt_isolation(self):
        session = InteractiveShellSession()
        for cmd in ["exit()", "quit()", "import sys; sys.exit(42)", "raise KeyboardInterrupt"]:
            out, more = session.push_line(cmd)
            self.assertFalse(more)
            self.assertTrue(len(out) > 0)
        # Ensure shell remains usable afterwards
        out, more = session.push_line("print(21 * 2)")
        self.assertIn("42", out)

    def test_interactive_shell_input_bridging(self):
        session = InteractiveShellSession(input_handler=lambda prompt: "mock_user_input")
        out, more = session.push_line("ans = input('Enter: '); print('Got:', ans)")
        self.assertFalse(more)
        self.assertIn("Got: mock_user_input", out)


class TestPythonLinterAndRunner(unittest.TestCase):
    """Test AST syntax analysis and script runner."""

    def test_valid_python_lint(self):
        code = "def add(a, b):\n    return a + b\n"
        diags, summary, used = PythonLinter.lint(content=code)
        self.assertEqual(len(diags), 0)
        self.assertIn("OK", summary)

    def test_syntax_error_detection(self):
        bad_code = "def broken(\n    print('unclosed')\n"
        diags, summary, used = PythonLinter.lint(content=bad_code)
        self.assertGreater(len(diags), 0)
        self.assertEqual(diags[0].severity, "error")
        self.assertEqual(diags[0].line, 1)

    def test_runner_init_and_execution(self):
        runner = PythonRunner()
        self.assertFalse(runner.is_running)

        done_event = threading.Event()
        outputs = []
        exit_codes = []

        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
            tf.write("import sys\nline = input('prompt>')\nprint('Result:', line)\n")
            script_path = tf.name

        try:
            def on_out(text, is_err):
                outputs.append(text)
                if "prompt>" in "".join(outputs):
                    runner.send_input("hello_world")

            def on_done(rc):
                exit_codes.append(rc)
                done_event.set()

            runner.run(script_path, on_output=on_out, on_finished=on_done)
            self.assertTrue(done_event.wait(timeout=5.0), "Script execution timed out")
            self.assertEqual(exit_codes, [0])
            self.assertIn("Result: hello_world", "".join(outputs))
        finally:
            if os.path.exists(script_path):
                os.unlink(script_path)


class TestEditorLogicAndPowerEditing(unittest.TestCase):
    """Test Retina font scaling steps and advanced power editing tools."""

    def test_zoom_steps(self):
        steps = RetinaEditor.ZOOM_STEPS
        self.assertIn(1.0, steps)
        self.assertEqual(steps[RetinaEditor.DEFAULT_ZOOM_INDEX], 1.00)
        self.assertTrue(all(steps[i] < steps[i+1] for i in range(len(steps)-1)))

    def test_gtksource_schemes_available(self):
        manager = GtkSource.StyleSchemeManager.get_default()
        schemes = manager.get_scheme_ids()
        self.assertTrue(len(schemes) > 0)
        self.assertIn('pythonpad-neon', schemes)
        neon_scheme = manager.get_scheme('pythonpad-neon')
        self.assertIsNotNone(neon_scheme)
        self.assertEqual(neon_scheme.get_name(), 'Neon Blue & White')

    def test_editor_null_byte_sanitization_and_atomic_save(self):
        gi.require_version('Gdk', '3.0')
        from gi.repository import Gdk
        if Gdk.Display.get_default() is None:
            self.skipTest("Requires active X11/Wayland display connection for GtkWidget instantiation")
        ed = RetinaEditor(file_path="/tmp/nonexistent_pythonpad_test_file.py")
        self.assertIsNotNone(ed.file_path)
        ed.set_text("a = 'hello\\x00world'\x00\nb = '# not a comment'\n")
        self.assertNotIn("\x00", ed.get_text())

        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
            temp_path = tf.name

        try:
            ed.file_encoding = "LATIN-1"
            ed.set_text("print('Unicode \\u2605 symbol')")
            ed.save_file(temp_path)
            self.assertEqual(ed.file_encoding, "UTF-8")
            with open(temp_path, "r", encoding="utf-8") as f:
                saved = f.read()
            self.assertIn("Unicode \\u2605 symbol", saved)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            if os.path.exists("/tmp/nonexistent_pythonpad_test_file.py"):
                os.unlink("/tmp/nonexistent_pythonpad_test_file.py")

    def test_gui_interactive_shell_and_f5_runner(self):
        gi.require_version('Gdk', '3.0')
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gdk, Gtk, GLib
        if Gdk.Display.get_default() is None:
            self.skipTest("Requires active X11/Wayland display connection for GUI verification")

        from pythonpad import PythonPadWindow
        win = PythonPadWindow(app=None)
        try:
            # 1. Verify bottom panel and Interactive Shell visibility & execution
            win.toggle_bottom_panel(force_show=True, tab_index=0)
            self.assertTrue(win.panel.get_visible(), "Bottom panel should be visible")
            self.assertTrue(win.panel.shell_view.get_visible(), "Interactive shell view should be visible")
            self.assertEqual(win.panel.notebook.get_visible_child_name(), "shell")

            win.panel.shell_entry.set_text("shell_check = 21 * 2; print('SHELL_OK:', shell_check)")
            win.panel._on_shell_submit(win.panel.shell_entry)

            buf = win.panel.shell_buffer
            shell_text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
            self.assertIn("SHELL_OK: 42", shell_text)

            # 2. Verify F5 script execution on saved file
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
                tf.write("print('F5_RUNNER_OK:', 123 + 456)\n")
                script_path = tf.name

            try:
                ed = win.get_current_editor()
                ed.load_file(script_path)
                win.run_active_script()
                self.assertEqual(win.panel.notebook.get_visible_child_name(), "console")

                # Pump GLib main context until runner finishes
                deadline = GLib.get_monotonic_time() + 4_000_000
                while GLib.get_monotonic_time() < deadline:
                    while Gtk.events_pending():
                        Gtk.main_iteration_do(False)
                    cbuf = win.panel.console_buffer
                    ctext = cbuf.get_text(cbuf.get_start_iter(), cbuf.get_end_iter(), False)
                    if "F5_RUNNER_OK: 579" in ctext and "Process finished" in ctext:
                        break

                cbuf = win.panel.console_buffer
                ctext = cbuf.get_text(cbuf.get_start_iter(), cbuf.get_end_iter(), False)
                self.assertIn("F5_RUNNER_OK: 579", ctext)
            finally:
                if os.path.exists(script_path):
                    os.unlink(script_path)
        finally:
            win.destroy()


class TestAppAssets(unittest.TestCase):
    """Test SVG icon and desktop file integrity."""

    def setUp(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

    def test_svg_icon_validity(self):
        svg_path = os.path.join(self.base_dir, "pythonpad.svg")
        self.assertTrue(os.path.exists(svg_path), "pythonpad.svg does not exist")

        tree = ET.parse(svg_path)
        root = tree.getroot()
        self.assertTrue(root.tag.endswith('svg'))
        self.assertEqual(root.attrib.get('viewBox'), '0 0 512 512')

    def test_desktop_file_exists(self):
        desktop_path = os.path.join(self.base_dir, "pythonpad.desktop")
        self.assertTrue(os.path.exists(desktop_path), "pythonpad.desktop does not exist")
        with open(desktop_path, 'r') as f:
            content = f.read()
        self.assertIn("[Desktop Entry]", content)
        self.assertIn("Name=PythonPad", content)
        self.assertIn("StartupWMClass=pythonpad", content)

    def test_scripts_executable(self):
        for script in ['run.sh', 'install.sh', 'pythonpad.py']:
            path = os.path.join(self.base_dir, script)
            self.assertTrue(os.access(path, os.X_OK), f"{script} is not executable")


if __name__ == '__main__':
    unittest.main()
