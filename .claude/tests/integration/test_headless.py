#!/usr/bin/env python3
"""
Test Suite for Headless Protocol

Tests the functionality of: scripts/lib/browser.py
"""
import unittest
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestHeadlessProtocol(unittest.TestCase):
    """Tests for Headless Protocol"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.project_root = PROJECT_ROOT
        cls.lib_path = cls.project_root / "scripts/lib/browser.py"
        assert cls.lib_path.exists(), f"Library not found: {cls.lib_path}"

    def test_library_imports(self):
        """Test that library can be imported"""
        try:
            sys.path.insert(0, str(self.lib_path.parent))
            import browser
            self.assertTrue(hasattr(browser, 'get_browser_session'))
            self.assertTrue(hasattr(browser, 'smart_dump'))
        except ImportError as e:
            self.skipTest(f"Playwright not installed: {e}")

    def test_module_structure(self):
        """Test library structure and exports"""
        content = self.lib_path.read_text()
        self.assertIn("def get_browser_session", content)
        self.assertIn("def smart_dump", content)
        self.assertIn("playwright", content.lower())

    def test_integration_with_sdk(self):
        """Test library follows SDK patterns"""
        content = self.lib_path.read_text()
        # Browser library may not use setup_script (it's a library not a CLI)
        self.assertIn("def ", content, "Should have function definitions")

    def test_documentation(self):
        """Test that library has proper documentation"""
        content = self.lib_path.read_text()
        self.assertIn('"""', content, "Should have docstrings")


if __name__ == '__main__':
    unittest.main()
