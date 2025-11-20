#!/usr/bin/env python3
"""
Stability tests for path resolution
Validates that scripts can find core library from any location.
"""
import sys
import os
import subprocess

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

def test_scratch_script_imports_core():
    """Test that scripts in scratch/ can import core library"""
    test_path = os.path.join(PROJECT_ROOT, "scratch", "test_path_scratch.py")

    try:
        # Create script using scaffolder
        result = subprocess.run(
            ["python3", os.path.join(PROJECT_ROOT, "scripts", "scaffold.py"),
             test_path, "Path test from scratch"],
            capture_output=True,
            check=True
        )

        # Try to run it (this will fail if imports don't work)
        result = subprocess.run(
            ["python3", test_path, "--help"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Script from scratch/ failed to import: {result.stderr}"

        print("✅ Scripts in scratch/ can import core library")

    finally:
        if os.path.exists(test_path):
            os.remove(test_path)

def test_nested_script_imports_core():
    """Test that scripts in scripts/category/ can import core library"""
    category_dir = os.path.join(PROJECT_ROOT, "scripts", "test_category")
    test_path = os.path.join(category_dir, "test_nested.py")

    try:
        # Create category directory
        os.makedirs(category_dir, exist_ok=True)

        # Create script using scaffolder
        subprocess.run(
            ["python3", os.path.join(PROJECT_ROOT, "scripts", "scaffold.py"),
             test_path, "Path test from nested dir"],
            capture_output=True,
            check=True
        )

        # Try to run it
        result = subprocess.run(
            ["python3", test_path, "--help"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Nested script failed to import: {result.stderr}"

        print("✅ Scripts in scripts/category/ can import core library")

    finally:
        if os.path.exists(category_dir):
            import shutil
            shutil.rmtree(category_dir)

def test_deeply_nested_script_imports_core():
    """Test that scripts in scripts/cat1/cat2/cat3/ can import core library"""
    deep_dir = os.path.join(PROJECT_ROOT, "scripts", "cat1", "cat2", "cat3")
    test_path = os.path.join(deep_dir, "test_deep.py")

    try:
        # Create deep directory structure
        os.makedirs(deep_dir, exist_ok=True)

        # Create script using scaffolder
        subprocess.run(
            ["python3", os.path.join(PROJECT_ROOT, "scripts", "scaffold.py"),
             test_path, "Path test from deeply nested dir"],
            capture_output=True,
            check=True
        )

        # Try to run it
        result = subprocess.run(
            ["python3", test_path, "--help"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Deeply nested script failed to import: {result.stderr}"

        print("✅ Scripts in deeply nested directories can import core library")

    finally:
        # Clean up entire cat1 directory
        cat1_dir = os.path.join(PROJECT_ROOT, "scripts", "cat1")
        if os.path.exists(cat1_dir):
            import shutil
            shutil.rmtree(cat1_dir)

def main():
    print("=" * 60)
    print("STABILITY TESTS: Path Resolution")
    print("=" * 60)

    tests = [
        test_scratch_script_imports_core,
        test_nested_script_imports_core,
        test_deeply_nested_script_imports_core,
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
