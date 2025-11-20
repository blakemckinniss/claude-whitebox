#!/usr/bin/env python3
"""
Integration tests for scripts/scaffold.py
Validates that scaffolder creates executable, valid scripts.
"""
import sys
import os
import subprocess
import tempfile
import shutil

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

def test_scaffolder_creates_file():
    """Test that scaffolder creates a file at the specified path"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "test_script.py")

        # Run scaffolder
        result = subprocess.run(
            ["python3", os.path.join(PROJECT_ROOT, "scripts", "scaffold.py"),
             test_path, "Test script"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Scaffolder failed: {result.stderr}"
        assert os.path.exists(test_path), "Scaffolder should create the file"
        assert os.access(test_path, os.X_OK), "File should be executable"

        print("✅ Scaffolder creates executable file")

def test_scaffolded_script_has_required_imports():
    """Test that scaffolded scripts import from core library"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "test_script.py")

        # Create script
        subprocess.run(
            ["python3", os.path.join(PROJECT_ROOT, "scripts", "scaffold.py"),
             test_path, "Test"],
            capture_output=True
        )

        # Read content
        with open(test_path, 'r') as f:
            content = f.read()

        assert "from core import" in content, "Should import from core"
        assert "setup_script" in content, "Should import setup_script"
        assert "finalize" in content, "Should import finalize"
        assert "logger" in content, "Should import logger"

        print("✅ Scaffolded script has required imports")

def test_scaffolded_script_has_docstring():
    """Test that scaffolded scripts include the description as docstring"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = os.path.join(tmpdir, "test_script.py")
        description = "This is a test description"

        # Create script
        subprocess.run(
            ["python3", os.path.join(PROJECT_ROOT, "scripts", "scaffold.py"),
             test_path, description],
            capture_output=True
        )

        # Read content
        with open(test_path, 'r') as f:
            content = f.read()

        assert description in content, "Description should be in docstring"

        print("✅ Scaffolded script includes description in docstring")

def test_scaffolded_script_accepts_help_flag():
    """Test that scaffolded scripts respond to --help"""
    # Create script in scratch (part of project, so imports work)
    test_path = os.path.join(PROJECT_ROOT, "scratch", "test_help_flag.py")

    try:
        # Create script
        subprocess.run(
            ["python3", os.path.join(PROJECT_ROOT, "scripts", "scaffold.py"),
             test_path, "Test help"],
            capture_output=True,
            check=True
        )

        # Test --help flag
        result = subprocess.run(
            ["python3", test_path, "--help"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, "Script should handle --help"
        assert "--dry-run" in result.stdout, "Help should mention --dry-run"
        assert "--debug" in result.stdout, "Help should mention --debug"

        print("✅ Scaffolded script responds to --help")

    finally:
        if os.path.exists(test_path):
            os.remove(test_path)

def test_scaffolded_script_accepts_dry_run():
    """Test that scaffolded scripts respond to --dry-run"""
    test_path = os.path.join(PROJECT_ROOT, "scratch", "test_dry_run.py")

    try:
        # Create script
        subprocess.run(
            ["python3", os.path.join(PROJECT_ROOT, "scripts", "scaffold.py"),
             test_path, "Test dry run"],
            capture_output=True,
            check=True
        )

        # Test --dry-run flag
        result = subprocess.run(
            ["python3", test_path, "--dry-run"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, "Script should run with --dry-run"
        assert "DRY RUN" in result.stdout or "DRY RUN" in result.stderr, \
            "Output should mention dry run mode"

        print("✅ Scaffolded script responds to --dry-run")

    finally:
        if os.path.exists(test_path):
            os.remove(test_path)

def main():
    print("=" * 60)
    print("INTEGRATION TESTS: Scaffolder (scripts/scaffold.py)")
    print("=" * 60)

    tests = [
        test_scaffolder_creates_file,
        test_scaffolded_script_has_required_imports,
        test_scaffolded_script_has_docstring,
        test_scaffolded_script_accepts_help_flag,
        test_scaffolded_script_accepts_dry_run,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: Unexpected error: {e}")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
