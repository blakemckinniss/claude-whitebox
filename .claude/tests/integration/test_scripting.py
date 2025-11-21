#!/usr/bin/env python3
"""
Test Suite for Scripting Protocol

Tests the functionality of: scripts/scaffold.py
"""
import unittest
import sys
import os
from pathlib import Path
import subprocess
import tempfile

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestScriptingProtocol(unittest.TestCase):
    """Tests for Scripting Protocol"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.project_root = PROJECT_ROOT
        cls.script_path = cls.project_root / "scripts/scaffold.py"
        assert cls.script_path.exists(), f"Script not found: {cls.script_path}"

    def test_dry_run_mode(self):
        """Test that help flag works (scaffold.py doesn't support --dry-run)"""
        result = subprocess.run(
            ["python3", str(self.script_path), "--help"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            timeout=10
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage:", result.stdout.lower())

    def test_basic_scaffolding(self):
        """Test creating a basic script"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_script.py"
            result = subprocess.run(
                ["python3", str(self.script_path), str(output_path),
                 "Test description"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=10
            )
            self.assertEqual(result.returncode, 0)
            self.assertTrue(output_path.exists(),
                           "Script file should be created")

            # Verify scaffolded script content
            content = output_path.read_text()
            self.assertIn("from core import", content)
            self.assertIn("setup_script", content)
            self.assertIn("Test description", content)

    def test_help_flag(self):
        """Test that --help flag works"""
        result = subprocess.run(
            ["python3", str(self.script_path), "--help"],
            capture_output=True,
            text=True,
            cwd=self.project_root
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage:", result.stdout.lower())

    def test_integration_with_core(self):
        """Test integration with core SDK library"""
        with open(self.script_path, 'r') as f:
            content = f.read()
            self.assertIn("from core import", content)


if __name__ == '__main__':
    unittest.main()
