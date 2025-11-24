#!/usr/bin/env python3
"""
Test File Operation Gate
Tests all validation scenarios in isolation
"""

import json
import subprocess
from pathlib import Path

PROJECT_DIR = Path.cwd()
HOOK_PATH = PROJECT_DIR / ".claude/hooks/file_operation_gate.py"


def run_hook(tool_name: str, tool_params: dict, session_id: str = "test", prompt: str = "") -> dict:
    """Run the hook with test data"""
    data = {
        "sessionId": session_id,
        "toolName": tool_name,
        "toolParams": tool_params,
        "prompt": prompt,
        "turn": 1,
    }

    result = subprocess.run(
        ["python3", str(HOOK_PATH)],
        input=json.dumps(data),
        capture_output=True,
        text=True,
    )

    return json.loads(result.stdout)


def test_read_nonexistent():
    """Test 1: Read to non-existent file"""
    result = run_hook("Read", {"file_path": "/tmp/nonexistent_file_12345.txt"})
    allowed = result["hookSpecificOutput"]["allowExecution"]
    assert not allowed, "Should block read to non-existent file"
    print("✅ Test 1: Read non-existent file - BLOCKED")


def test_read_directory():
    """Test 2: Read to directory"""
    result = run_hook("Read", {"file_path": ".claude/hooks"})
    allowed = result["hookSpecificOutput"]["allowExecution"]
    assert not allowed, "Should block read to directory"
    print("✅ Test 2: Read directory - BLOCKED")


def test_read_valid():
    """Test 3: Valid read"""
    result = run_hook("Read", {"file_path": "CLAUDE.md"})
    allowed = result["hookSpecificOutput"]["allowExecution"]
    assert allowed, "Should allow valid read"
    print("✅ Test 3: Valid read - ALLOWED")


def test_write_without_read():
    """Test 4: Write to existing file without reading first"""
    # Create a test file
    test_file = PROJECT_DIR / "scratch/test_existing.txt"
    test_file.write_text("existing content")

    try:
        result = run_hook("Write", {"file_path": str(test_file)})
        allowed = result["hookSpecificOutput"]["allowExecution"]
        assert not allowed, "Should block write to existing file without read"
        print("✅ Test 4: Write without read - BLOCKED")
    finally:
        test_file.unlink(missing_ok=True)


def test_write_to_directory():
    """Test 5: Write to directory path"""
    result = run_hook("Write", {"file_path": ".claude/hooks"})
    allowed = result["hookSpecificOutput"]["allowExecution"]
    assert not allowed, "Should block write to directory"
    print("✅ Test 5: Write to directory - BLOCKED")


def test_write_new_file():
    """Test 6: Write new file (should succeed)"""
    test_file = PROJECT_DIR / "scratch/new_test_file.txt"
    test_file.unlink(missing_ok=True)  # Ensure it doesn't exist

    try:
        result = run_hook("Write", {"file_path": str(test_file)})
        allowed = result["hookSpecificOutput"]["allowExecution"]
        assert allowed, "Should allow write to new file"
        print("✅ Test 6: Write new file - ALLOWED")
    finally:
        test_file.unlink(missing_ok=True)


def test_edit_nonexistent():
    """Test 7: Edit non-existent file"""
    result = run_hook("Edit", {"file_path": "scratch/nonexistent.py"})
    allowed = result["hookSpecificOutput"]["allowExecution"]
    assert not allowed, "Should block edit to non-existent file"
    print("✅ Test 7: Edit non-existent file - BLOCKED")


def test_edit_without_read():
    """Test 8: Edit existing file without reading first"""
    # Use unique session to avoid state pollution from test_read_valid
    result = run_hook("Edit", {"file_path": "CLAUDE.md"}, session_id="test_session_8")
    allowed = result["hookSpecificOutput"]["allowExecution"]
    assert not allowed, "Should block edit without prior read"
    print("✅ Test 8: Edit without read - BLOCKED")


def test_read_then_edit():
    """Test 9: Read then Edit (should succeed)"""
    # First read
    session_id = "test_session_9"
    result1 = run_hook("Read", {"file_path": "CLAUDE.md"}, session_id=session_id)
    assert result1["hookSpecificOutput"]["allowExecution"], "Read should succeed"

    # Then edit
    result2 = run_hook("Edit", {"file_path": "CLAUDE.md"}, session_id=session_id)
    allowed = result2["hookSpecificOutput"]["allowExecution"]
    assert allowed, "Should allow edit after read"
    print("✅ Test 9: Read then Edit - ALLOWED")


def test_sudo_bypass():
    """Test 10: SUDO bypass"""
    result = run_hook(
        "Read",
        {"file_path": "/tmp/nonexistent.txt"},
        prompt="SUDO override"
    )
    allowed = result["hookSpecificOutput"]["allowExecution"]
    assert allowed, "SUDO should bypass validation"
    print("✅ Test 10: SUDO bypass - ALLOWED")


if __name__ == "__main__":
    print("🧪 File Operation Gate Tests\n")

    tests = [
        test_read_nonexistent,
        test_read_directory,
        test_read_valid,
        test_write_without_read,
        test_write_to_directory,
        test_write_new_file,
        test_edit_nonexistent,
        test_edit_without_read,
        test_read_then_edit,
        test_sudo_bypass,
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
            print(f"💥 {test.__name__}: {e}")
            failed += 1

    print(f"\n📊 Results: {passed} passed, {failed} failed")

    if failed > 0:
        exit(1)
