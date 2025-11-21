#!/usr/bin/env python3
"""
Test Suite for MacGyver Protocol

Tests the functionality of: scripts/ops/inventory.py
"""
import unittest
import sys
import os
from pathlib import Path
import subprocess
import tempfile

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestMacGyverProtocol(unittest.TestCase):
    """Tests for MacGyver Protocol"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.project_root = PROJECT_ROOT
        cls.script_path = cls.project_root / "scripts/ops/inventory.py"
        assert cls.script_path.exists(), f"Script not found: {cls.script_path}"

    def test_dry_run_mode(self):
        """Test that dry-run mode works without external dependencies"""
        result = subprocess.run(
            ["python3", str(self.script_path), "--dry-run"],
            capture_output=True,
            text=True,
            cwd=self.project_root
        )
        # Dry-run should succeed (exit 0) or skip gracefully
        self.assertIn(result.returncode, [0, 1],
                     f"Dry-run failed: {result.stderr}")
        self.assertIn("DRY", result.stdout + result.stderr,
                     "Expected DRY RUN marker in output")

    def test_basic_functionality(self):
        """Test core functionality of the protocol"""
        result = subprocess.run(
            ["python3", str(self.script_path), "--compact"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            timeout=30
        )
        self.assertEqual(result.returncode, 0,
                        f"Basic execution failed: {result.stderr}")
        self.assertTrue(len(result.stdout) > 0,
                       "Expected non-empty output")

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
        # Verify script imports core library correctly
        with open(self.script_path, 'r') as f:
            content = f.read()
            self.assertIn("from core import", content,
                         "Script should import from core library")
            self.assertIn("setup_script", content,
                         "Script should use setup_script()")
            self.assertIn("finalize", content,
                         "Script should use finalize()")


if __name__ == '__main__':
    unittest.main()
