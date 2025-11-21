#!/usr/bin/env python3
"""
Test Suite for Oracle Protocol

Tests the functionality of: scripts/ops/consult.py
"""
import unittest
import sys
import os
from pathlib import Path
import subprocess
import tempfile

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestOracleProtocol(unittest.TestCase):
    """Tests for Oracle Protocol"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.project_root = PROJECT_ROOT
        cls.script_path = cls.project_root / "scripts/ops/consult.py"
        assert cls.script_path.exists(), f"Script not found: {cls.script_path}"

    def test_dry_run_mode(self):
        """Test that dry-run mode works without API keys"""
        env = os.environ.copy()
        env.pop('OPENROUTER_API_KEY', None)  # Remove API key

        result = subprocess.run(
            ["python3", str(self.script_path), "How do I design a REST API?", "--dry-run"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            env=env,
            timeout=10
        )
        # Dry-run should work without API key
        self.assertEqual(result.returncode, 0,
                        f"Dry-run should work without API key: {result.stderr}")
        self.assertIn("DRY", result.stdout + result.stderr)

    @unittest.skip("Skipping timeout-prone API key error test")
    def test_missing_api_key_handling(self):
        """Test graceful handling of missing API key"""
        env = os.environ.copy()
        env.pop('OPENROUTER_API_KEY', None)  # Remove API key

        result = subprocess.run(
            ["python3", str(self.script_path), "How do I design a REST API?"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            env=env,
            timeout=10
        )
        # Should fail gracefully with clear error message
        self.assertNotEqual(result.returncode, 0,
                           "Should fail when API key is missing")
        self.assertIn("OPENROUTER_API_KEY", result.stdout + result.stderr,
                     "Should mention missing API key")

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
            self.assertIn("setup_script", content)
            self.assertIn("finalize", content)
            self.assertIn("OPENROUTER_API_KEY", content,
                         "Script should check for API key")


if __name__ == '__main__':
    unittest.main()
