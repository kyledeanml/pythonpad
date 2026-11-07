#!/usr/bin/env python3
"""
Unit and Integration Tests for RetinaPad
Tests editor logic, retina zoom scaling, desktop validation, and icon integrity.
"""

import os
import unittest
import xml.etree.ElementTree as ET
import gi

gi.require_version('GtkSource', '4')
from gi.repository import GtkSource

from editor import RetinaEditor


class TestRetinaEditorLogic(unittest.TestCase):
    """Test retina zoom calculations and scaling levels."""

    def test_zoom_steps(self):
        steps = RetinaEditor.ZOOM_STEPS
        self.assertIn(1.0, steps)
        self.assertEqual(steps[RetinaEditor.DEFAULT_ZOOM_INDEX], 1.00)
        self.assertTrue(all(steps[i] < steps[i+1] for i in range(len(steps)-1)))

    def test_zoom_percent_calculation(self):
        steps = RetinaEditor.ZOOM_STEPS
        for s in steps:
            percent = int(round(s * 100))
            self.assertGreaterEqual(percent, 50)
            self.assertLessEqual(percent, 300)

    def test_gtksource_schemes_available(self):
        manager = GtkSource.StyleSchemeManager.get_default()
        schemes = manager.get_scheme_ids()
        self.assertTrue(len(schemes) > 0)
        # Check standard schemes
        self.assertTrue(any(s in schemes for s in ['xed', 'classic', 'tango', 'oblivion']))

    def test_gtksource_languages_available(self):
        manager = GtkSource.LanguageManager.get_default()
        lang_py = manager.get_language('python3') or manager.get_language('python')
        self.assertIsNotNone(lang_py)


class TestAppAssets(unittest.TestCase):
    """Test SVG icon and desktop file integrity."""

    def setUp(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

    def test_svg_icon_validity(self):
        svg_path = os.path.join(self.base_dir, "retinapad.svg")
        self.assertTrue(os.path.exists(svg_path), "retinapad.svg does not exist")

        tree = ET.parse(svg_path)
        root = tree.getroot()
        self.assertTrue(root.tag.endswith('svg'))
        self.assertEqual(root.attrib.get('viewBox'), '0 0 512 512')
        self.assertEqual(root.attrib.get('width'), '512')
        self.assertEqual(root.attrib.get('height'), '512')

    def test_desktop_file_exists(self):
        desktop_path = os.path.join(self.base_dir, "retinapad.desktop")
        self.assertTrue(os.path.exists(desktop_path), "retinapad.desktop does not exist")
        with open(desktop_path, 'r') as f:
            content = f.read()
        self.assertIn("[Desktop Entry]", content)
        self.assertIn("Name=RetinaPad", content)
        self.assertIn("Categories=GTK;GNOME;Utility;TextEditor;", content)

    def test_scripts_executable(self):
        for script in ['run.sh', 'install.sh', 'retinapad.py']:
            path = os.path.join(self.base_dir, script)
            self.assertTrue(os.access(path, os.X_OK), f"{script} is not executable")


if __name__ == '__main__':
    unittest.main()
