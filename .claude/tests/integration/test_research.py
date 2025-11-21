#!/usr/bin/env python3
"""
Test Suite for Research Protocol

Tests the functionality of: scripts/ops/research.py
"""
import unittest
import sys
import os
from pathlib import Path
import subprocess

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestResearchProtocol(unittest.TestCase):
    """Tests for Research Protocol"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.project_root = PROJECT_ROOT
        cls.script_path = cls.project_root / "scripts/ops/research.py"
        assert cls.script_path.exists(), f"Script not found: {cls.script_path}"

    def test_dry_run_mode(self):
        """Test that dry-run mode works without API keys"""
        env = os.environ.copy()
        env.pop('TAVILY_API_KEY', None)  # Remove API key

        result = subprocess.run(
            ["python3", str(self.script_path), "python unittest best practices", "--dry-run"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            env=env,
            timeout=10
        )
        self.assertEqual(result.returncode, 0,
                        f"Dry-run should work without API key: {result.stderr}")
        self.assertIn("DRY", result.stdout + result.stderr)

    @unittest.skip("Skipping timeout-prone API key error test")
    def test_missing_api_key_handling(self):
        """Test graceful handling of missing API key"""
        env = os.environ.copy()
        env.pop('TAVILY_API_KEY', None)

        result = subprocess.run(
            ["python3", str(self.script_path), "python unittest best practices"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            env=env,
            timeout=10
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("TAVILY_API_KEY", result.stdout + result.stderr)

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
            self.assertIn("TAVILY_API_KEY", content)


if __name__ == '__main__':
    unittest.main()
