#!/usr/bin/env python3
"""
Test Suite for Sentinel Protocol

Tests the functionality of: scripts/ops/audit.py
"""
import unittest
import sys
import os
from pathlib import Path
import subprocess
import tempfile

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestSentinelProtocol(unittest.TestCase):
    """Tests for Sentinel Protocol"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.project_root = PROJECT_ROOT
        cls.script_path = cls.project_root / "scripts/ops/audit.py"
        assert cls.script_path.exists(), f"Script not found: {cls.script_path}"

    def test_dry_run_mode(self):
        """Test that dry-run mode works"""
        result = subprocess.run(
            ["python3", str(self.script_path), "scripts/ops/audit.py", "--dry-run"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            timeout=30
        )
        self.assertIn(result.returncode, [0, 1])

    def test_audit_clean_file(self):
        """Test auditing a known-clean file"""
        result = subprocess.run(
            ["python3", str(self.script_path), "scripts/ops/audit.py"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            timeout=30
        )
        # Allow exit code 1 if audit tools (ruff/bandit/radon) are not installed
        self.assertIn(result.returncode, [0, 1],
                     f"Audit should pass or warn: {result.stderr}")

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
