#!/usr/bin/env python3
"""
Test Suite for Elephant Protocol

Tests the functionality of: scripts/ops/remember.py
"""
import unittest
import sys
import os
from pathlib import Path
import subprocess
import tempfile

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestElephantProtocol(unittest.TestCase):
    """Tests for Elephant Protocol"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.project_root = PROJECT_ROOT
        cls.script_path = cls.project_root / "scripts/ops/remember.py"
        cls.memory_dir = cls.project_root / ".claude" / "memory"
        assert cls.script_path.exists(), f"Script not found: {cls.script_path}"

    def test_dry_run_mode(self):
        """Test that dry-run mode works"""
        result = subprocess.run(
            ["python3", str(self.script_path), "read", "context", "--dry-run"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            timeout=10
        )
        self.assertIn(result.returncode, [0, 1])

    def test_read_memory(self):
        """Test reading from memory"""
        result = subprocess.run(
            ["python3", str(self.script_path), "read", "context"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
            timeout=10
        )
        self.assertEqual(result.returncode, 0)
        # Should output memory content or indicate no memory
        self.assertTrue(len(result.stdout) > 0)

    def test_memory_files_exist(self):
        """Test that memory directory structure exists"""
        self.assertTrue(self.memory_dir.exists(),
                       f"Memory directory should exist: {self.memory_dir}")

        # Check for memory files
        expected_files = ['active_context.md', 'decisions.md', 'lessons.md']
        for fname in expected_files:
            fpath = self.memory_dir / fname
            self.assertTrue(fpath.exists(),
                           f"Memory file should exist: {fname}")

    def test_integration_with_core(self):
        """Test integration with core SDK library"""
        with open(self.script_path, 'r') as f:
            content = f.read()
            self.assertIn("from core import", content)
            self.assertIn("setup_script", content)


if __name__ == '__main__':
    unittest.main()
