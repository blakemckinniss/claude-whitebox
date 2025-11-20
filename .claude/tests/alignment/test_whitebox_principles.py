#!/usr/bin/env python3
"""
Alignment tests for Whitebox Engineering principles
Validates that the SDK enforces transparency and safety standards.
"""
import sys
import os
import subprocess

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

def test_all_scripts_have_dry_run():
    """Test that all scaffolded scripts support --dry-run flag"""
    test_path = os.path.join(PROJECT_ROOT, "scratch", "test_alignment.py")

    try:
        # Create script
        subprocess.run(
            ["python3", os.path.join(PROJECT_ROOT, "scripts", "scaffold.py"),
             test_path, "Alignment test"],
            capture_output=True,
            check=True
        )

        # Check --help output
        result = subprocess.run(
            ["python3", test_path, "--help"],
            capture_output=True,
            text=True
        )

        assert "--dry-run" in result.stdout, \
            "All scripts must support --dry-run flag (Whitebox principle: Safety)"

        print("✅ All scaffolded scripts support --dry-run")

    finally:
        if os.path.exists(test_path):
            os.remove(test_path)

def test_all_scripts_use_logger():
    """Test that all scaffolded scripts import and use logger"""
    test_path = os.path.join(PROJECT_ROOT, "scratch", "test_logger.py")

    try:
        # Create script
        subprocess.run(
            ["python3", os.path.join(PROJECT_ROOT, "scripts", "scaffold.py"),
             test_path, "Logger test"],
            capture_output=True,
            check=True
        )

        # Read content
        with open(test_path, 'r') as f:
            content = f.read()

        assert "from core import" in content and "logger" in content, \
            "Scripts must import logger from core (Whitebox principle: Transparency)"

        assert "logger.info" in content or "logger.warning" in content or "logger.error" in content, \
            "Scripts must use logger for output (not print)"

        print("✅ All scaffolded scripts use standardized logging")

    finally:
        if os.path.exists(test_path):
            os.remove(test_path)

def test_all_scripts_import_from_core():
    """Test that all scaffolded scripts import from core library"""
    test_path = os.path.join(PROJECT_ROOT, "scratch", "test_imports.py")

    try:
        # Create script
        subprocess.run(
            ["python3", os.path.join(PROJECT_ROOT, "scripts", "scaffold.py"),
             test_path, "Import test"],
            capture_output=True,
            check=True
        )

        # Read content
        with open(test_path, 'r') as f:
            content = f.read()

        required_imports = ["setup_script", "finalize", "logger"]

        for import_name in required_imports:
            assert import_name in content, \
                f"Scripts must import {import_name} from core (Whitebox principle: Consistency)"

        print("✅ All scaffolded scripts import from core library")

    finally:
        if os.path.exists(test_path):
            os.remove(test_path)

def test_all_scripts_have_docstrings():
    """Test that all scaffolded scripts have docstrings"""
    test_path = os.path.join(PROJECT_ROOT, "scratch", "test_docstring.py")
    description = "Test script with description"

    try:
        # Create script
        subprocess.run(
            ["python3", os.path.join(PROJECT_ROOT, "scripts", "scaffold.py"),
             test_path, description],
            capture_output=True,
            check=True
        )

        # Read content
        with open(test_path, 'r') as f:
            content = f.read()

        assert '"""' in content, "Scripts must have docstrings (Whitebox principle: Documentation)"
        assert description in content, "Docstring must contain the description"

        print("✅ All scaffolded scripts have docstrings")

    finally:
        if os.path.exists(test_path):
            os.remove(test_path)

def test_core_library_is_readable():
    """Test that core library code is human-readable Python"""
    core_path = os.path.join(PROJECT_ROOT, "scripts", "lib", "core.py")

    assert os.path.exists(core_path), "Core library must exist"

    # Try to parse it
    with open(core_path, 'r') as f:
        code = f.read()

    try:
        compile(code, core_path, 'exec')
        print("✅ Core library is valid, readable Python code (Whitebox principle: Transparency)")
    except SyntaxError as e:
        raise AssertionError(f"Core library has syntax errors: {e}")

def test_no_obfuscated_code():
    """Test that scaffolded scripts contain no obfuscated code"""
    test_path = os.path.join(PROJECT_ROOT, "scratch", "test_obfuscation.py")

    try:
        # Create script
        subprocess.run(
            ["python3", os.path.join(PROJECT_ROOT, "scripts", "scaffold.py"),
             test_path, "Obfuscation test"],
            capture_output=True,
            check=True
        )

        # Read content
        with open(test_path, 'r') as f:
            content = f.read()

        # Check for signs of obfuscation
        forbidden_patterns = ["exec(", "eval(", "compile(", "__import__"]

        for pattern in forbidden_patterns:
            assert pattern not in content, \
                f"Scripts must not contain {pattern} (Whitebox principle: No Magic)"

        print("✅ Scaffolded scripts contain no obfuscated code")

    finally:
        if os.path.exists(test_path):
            os.remove(test_path)

def main():
    print("=" * 60)
    print("ALIGNMENT TESTS: Whitebox Engineering Principles")
    print("=" * 60)

    tests = [
        test_all_scripts_have_dry_run,
        test_all_scripts_use_logger,
        test_all_scripts_import_from_core,
        test_all_scripts_have_docstrings,
        test_core_library_is_readable,
        test_no_obfuscated_code,
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
