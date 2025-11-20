#!/usr/bin/env python3
"""
Integration tests for scripts/index.py
Validates that indexer finds and catalogs scripts correctly.
"""
import sys
import os
import subprocess
import shutil

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
INDEX_FILE = os.path.join(PROJECT_ROOT, ".claude", "skills", "tool_index.md")

def test_indexer_runs_without_error():
    """Test that indexer executes successfully"""
    result = subprocess.run(
        ["python3", os.path.join(PROJECT_ROOT, "scripts", "index.py")],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Indexer failed: {result.stderr}"
    print("✅ Indexer runs without error")

def test_indexer_creates_output_file():
    """Test that indexer creates tool_index.md"""
    # Run indexer
    subprocess.run(
        ["python3", os.path.join(PROJECT_ROOT, "scripts", "index.py")],
        capture_output=True,
        check=True
    )

    assert os.path.exists(INDEX_FILE), "Indexer should create tool_index.md"
    print("✅ Indexer creates output file")

def test_indexer_finds_existing_scripts():
    """Test that indexer detects existing scripts"""
    # Create a test script
    test_category = os.path.join(PROJECT_ROOT, "scripts", "test_indexer")
    test_script = os.path.join(test_category, "test_tool.py")

    try:
        os.makedirs(test_category, exist_ok=True)

        # Create script with scaffolder
        subprocess.run(
            ["python3", os.path.join(PROJECT_ROOT, "scripts", "scaffold.py"),
             test_script, "Test tool for indexer"],
            capture_output=True,
            check=True
        )

        # Run indexer
        subprocess.run(
            ["python3", os.path.join(PROJECT_ROOT, "scripts", "index.py")],
            capture_output=True,
            check=True
        )

        # Check index file contains our script
        with open(INDEX_FILE, 'r') as f:
            content = f.read()

        assert "test_indexer/test_tool.py" in content, \
            "Indexer should find the test script"
        assert "Test tool for indexer" in content, \
            "Indexer should extract docstring"

        print("✅ Indexer finds and catalogs scripts")

    finally:
        if os.path.exists(test_category):
            shutil.rmtree(test_category)
        # Re-run indexer to clean up
        subprocess.run(
            ["python3", os.path.join(PROJECT_ROOT, "scripts", "index.py")],
            capture_output=True
        )

def test_indexer_skips_lib_directory():
    """Test that indexer ignores scripts/lib/"""
    # Run indexer
    subprocess.run(
        ["python3", os.path.join(PROJECT_ROOT, "scripts", "index.py")],
        capture_output=True,
        check=True
    )

    # Check that lib/core.py is NOT in the index
    with open(INDEX_FILE, 'r') as f:
        content = f.read()

    assert "lib/core.py" not in content, "Indexer should skip lib directory"
    print("✅ Indexer skips lib directory")

def test_indexer_skips_meta_scripts():
    """Test that indexer ignores scaffold.py and index.py"""
    # Run indexer
    subprocess.run(
        ["python3", os.path.join(PROJECT_ROOT, "scripts", "index.py")],
        capture_output=True,
        check=True
    )

    # Check that meta scripts are NOT in the index table
    with open(INDEX_FILE, 'r') as f:
        content = f.read()

    # Extract only the table section (between headers and footer)
    table_start = content.find("|:-------|")
    table_end = content.find("---\n", table_start)
    table_content = content[table_start:table_end] if table_start != -1 and table_end != -1 else content

    assert "scaffold.py" not in table_content, "Indexer should skip scaffold.py"
    assert "`scripts/index.py`" not in table_content, "Indexer should skip index.py from script list"
    print("✅ Indexer skips meta scripts")

def main():
    print("=" * 60)
    print("INTEGRATION TESTS: Indexer (scripts/index.py)")
    print("=" * 60)

    tests = [
        test_indexer_runs_without_error,
        test_indexer_creates_output_file,
        test_indexer_finds_existing_scripts,
        test_indexer_skips_lib_directory,
        test_indexer_skips_meta_scripts,
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
