#!/usr/bin/env python3
"""
Unit and Integration Tests for PythonPad
Tests interactive REPL, system interpreter execution, advanced editing operations,
retina zoom scaling, and desktop asset integrity.
"""

import os
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

    def test_runner_init(self):
        runner = PythonRunner()
        self.assertFalse(runner.is_running)


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
