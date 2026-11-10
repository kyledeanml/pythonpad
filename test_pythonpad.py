#!/usr/bin/env python3
"""
Unit and Integration Tests for PythonPad
Tests interactive REPL, system interpreter execution, advanced editing operations,
retina zoom scaling, and desktop asset integrity.
"""

import os
import sys
import tempfile

sys.dont_write_bytecode = True
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
        code = '"""Module docstring."""\n\n\ndef add(a, b):\n    """Add two numbers."""\n    return a + b\n'
        diags, summary, used = PythonLinter.lint(content=code)
        self.assertEqual(len(diags), 0)
        self.assertTrue("Clean" in summary or "OK" in summary)

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
            ed.set_text("print('Unicode \u2605 symbol')")
            ed.save_file(temp_path)
            self.assertEqual(ed.file_encoding, "UTF-8")
            with open(temp_path, "r", encoding="utf-8") as f:
                saved = f.read()
            self.assertIn("Unicode \u2605 symbol", saved)
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
        self.assertIsNotNone(RetinaEditor._get_watermark_pixbuf())

    def test_desktop_file_exists(self):
        desktop_path = os.path.join(self.base_dir, "pythonpad.desktop")
        self.assertTrue(os.path.exists(desktop_path), "pythonpad.desktop does not exist")
        with open(desktop_path, 'r') as f:
            content = f.read()
        self.assertIn("[Desktop Entry]", content)
        self.assertIn("Name=PythonPad", content)
        self.assertIn("StartupWMClass=pythonpad", content)
        self.assertIn("text/plain;", content)
        self.assertIn("text/x-python;", content)

        install_path = os.path.join(self.base_dir, "install.sh")
        with open(install_path, 'r') as f:
            install_content = f.read()
        self.assertIn("xdg-mime default pythonpad.desktop", install_content)
        self.assertIn("mimeapps.list", install_content)

    def test_scripts_executable(self):
        for script in ['run.sh', 'install.sh', 'pythonpad.py', 'project_tree.py']:
            path = os.path.join(self.base_dir, script)
            self.assertTrue(os.access(path, os.X_OK) or script == 'project_tree.py', f"{script} is not accessible")


class TestProjectSidebar(unittest.TestCase):
    """Test Project File Structure sidebar, tree scanning, filtering, and toggle operations."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="pythonpad_proj_test_")
        # Create a mock project structure:
        # root/
        #   src/
        #     main.py
        #     utils.py
        #   tests/
        #     test_main.py
        #   __pycache__/
        #     main.cpython-312.pyc
        #   .git/
        #     config
        #   .hidden_file
        #   README.md
        #   config.json
        os.makedirs(os.path.join(self.tmp_dir, "src"), exist_ok=True)
        os.makedirs(os.path.join(self.tmp_dir, "tests"), exist_ok=True)
        os.makedirs(os.path.join(self.tmp_dir, "__pycache__"), exist_ok=True)
        os.makedirs(os.path.join(self.tmp_dir, ".git"), exist_ok=True)

        for p in [
            os.path.join(self.tmp_dir, "src", "main.py"),
            os.path.join(self.tmp_dir, "src", "utils.py"),
            os.path.join(self.tmp_dir, "tests", "test_main.py"),
            os.path.join(self.tmp_dir, "__pycache__", "main.cpython-312.pyc"),
            os.path.join(self.tmp_dir, ".git", "config"),
            os.path.join(self.tmp_dir, ".hidden_file"),
            os.path.join(self.tmp_dir, "README.md"),
            os.path.join(self.tmp_dir, "config.json"),
        ]:
            with open(p, "w", encoding="utf-8") as f:
                f.write(f"# Content of {os.path.basename(p)}\n")

    def tearDown(self):
        if os.path.exists(self.tmp_dir):
            import shutil
            shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_project_tree_scanning_and_filtering(self):
        gi.require_version('Gdk', '3.0')
        from gi.repository import Gdk
        if Gdk.Display.get_default() is None:
            self.skipTest("Requires active X11/Wayland display connection for GtkWidget instantiation")

        from project_tree import ProjectSidebar
        sidebar = ProjectSidebar(self.tmp_dir)
        self.assertEqual(sidebar.get_project_root(), self.tmp_dir)

        # Inspect root items in tree store
        store = sidebar.store
        root_items = []
        is_dirs = []
        for row in store:
            root_items.append(row[ProjectSidebar.COL_NAME])
            is_dirs.append(row[ProjectSidebar.COL_IS_DIR])

        # Directories first: src, tests
        self.assertIn("src", root_items)
        self.assertIn("tests", root_items)
        self.assertIn("README.md", root_items)
        self.assertIn("config.json", root_items)

        # Filtered items must NOT be present
        self.assertNotIn("__pycache__", root_items)
        self.assertNotIn(".git", root_items)
        self.assertNotIn(".hidden_file", root_items)

        # Check folders come first
        src_idx = root_items.index("src")
        tests_idx = root_items.index("tests")
        readme_idx = root_items.index("README.md")
        self.assertTrue(src_idx < readme_idx)
        self.assertTrue(tests_idx < readme_idx)

        # Test expand src
        src_iter = None
        for row in store:
            if row[ProjectSidebar.COL_NAME] == "src":
                src_iter = row.iter
                break
        self.assertIsNotNone(src_iter)

        sidebar._ensure_dir_loaded(src_iter, os.path.join(self.tmp_dir, "src"))
        src_children = []
        child = store.iter_children(src_iter)
        while child:
            src_children.append(store.get_value(child, ProjectSidebar.COL_NAME))
            child = store.iter_next(child)

        self.assertIn("main.py", src_children)
        self.assertIn("utils.py", src_children)

    def test_project_sidebar_toggle_and_tab_integration(self):
        gi.require_version('Gdk', '3.0')
        from gi.repository import Gdk
        if Gdk.Display.get_default() is None:
            self.skipTest("Requires active X11/Wayland display connection for GUI verification")

        from pythonpad import PythonPadWindow
        win = PythonPadWindow(app=None, initial_files=[self.tmp_dir])
        try:
            self.assertEqual(win.project_sidebar.get_project_root(), self.tmp_dir)
            self.assertTrue(win.project_sidebar.get_visible())
            self.assertTrue(win.btn_sidebar.get_active())

            # 1. Test clicking sidebar off (one-off script mode)
            win.toggle_project_sidebar(False)
            self.assertFalse(win.project_sidebar.get_visible())
            self.assertFalse(win.btn_sidebar.get_active())

            # 2. Test clicking sidebar on (project mode)
            win.toggle_project_sidebar(True)
            self.assertTrue(win.project_sidebar.get_visible())
            self.assertTrue(win.btn_sidebar.get_active())

            # 3. Test opening file from tree into tab
            main_py_path = os.path.join(self.tmp_dir, "src", "main.py")
            win.open_file_from_tree(main_py_path)
            self.assertEqual(win.get_current_editor().file_path, main_py_path)
            self.assertIn("main.py", win.get_title())

            # 4. Opening existing file should focus existing tab rather than duplicate
            config_json_path = os.path.join(self.tmp_dir, "config.json")
            win.open_file_from_tree(config_json_path)
            self.assertEqual(win.notebook_tabs.get_n_pages(), 2)

            win.open_file_from_tree(main_py_path)
            self.assertEqual(win.notebook_tabs.get_n_pages(), 2)
            self.assertEqual(win.get_current_editor().file_path, main_py_path)
        finally:
            win.destroy()

    def test_project_sidebar_no_blank_state_and_auto_root(self):
        gi.require_version('Gdk', '3.0')
        from gi.repository import Gdk
        if Gdk.Display.get_default() is None:
            self.skipTest("Requires active X11/Wayland display connection for GUI verification")

        from pythonpad import PythonPadWindow
        win = PythonPadWindow(app=None)
        try:
            # 1. Sidebar should not be blank: scrolled_tree must be visible
            self.assertTrue(win.project_sidebar.scrolled_tree.get_visible())
            self.assertGreater(len(win.project_sidebar.store), 0)

            # 2. When opening a script, project root automatically sets to parent folder
            test_file = os.path.join(self.tmp_dir, "src", "main.py")
            win.new_tab(test_file)
            self.assertEqual(win.project_sidebar.get_project_root(), os.path.dirname(test_file))
        finally:
            win.destroy()


if __name__ == '__main__':
    unittest.main()
