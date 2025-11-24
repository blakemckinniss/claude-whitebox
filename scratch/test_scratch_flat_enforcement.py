#!/usr/bin/env python3
"""
Test suite for scratch flat structure enforcement
Validates that the hook correctly blocks nested directory creation
"""
import subprocess
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd()
HOOK_PATH = PROJECT_ROOT / ".claude/hooks/scratch_flat_enforcer.py"

def test_hook(tool_name: str, tool_params: dict, prompt: str = "") -> dict:
    """Test the hook with given inputs"""
    input_data = {
        "sessionId": "test",
        "toolName": tool_name,
        "toolParams": tool_params,
        "prompt": prompt,
    }

    result = subprocess.run(
        ["python3", str(HOOK_PATH)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
    )

    try:
        return json.loads(result.stdout)
    except:
        print(f"Failed to parse output: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        return {}


def test_mkdir_blocked():
    """Test that mkdir scratch/subdir is blocked"""
    result = test_hook("Bash", {"command": "mkdir scratch/auth"})

    assert result["hookSpecificOutput"]["permissionDecision"] == "deny", \
        "Should block mkdir scratch/subdir"
    assert "SCRATCH FLAT STRUCTURE VIOLATION" in result["hookSpecificOutput"]["permissionDecisionReason"]
    print("✅ Blocked: mkdir scratch/auth")


def test_mkdir_p_blocked():
    """Test that mkdir -p scratch/nested/deep is blocked"""
    result = test_hook("Bash", {"command": "mkdir -p scratch/nested/deep"})

    assert result["hookSpecificOutput"]["permissionDecision"] == "deny", \
        "Should block mkdir -p scratch/nested/deep"
    print("✅ Blocked: mkdir -p scratch/nested/deep")


def test_write_nested_blocked():
    """Test that Write to scratch/subdir/file.py is blocked"""
    result = test_hook("Write", {"file_path": f"{PROJECT_ROOT}/scratch/auth/test.py"})

    assert result["hookSpecificOutput"]["permissionDecision"] == "deny", \
        "Should block Write to scratch/subdir/file.py"
    assert "SCRATCH FLAT STRUCTURE VIOLATION" in result["hookSpecificOutput"]["permissionDecisionReason"]
    print("✅ Blocked: Write scratch/auth/test.py")


def test_write_flat_allowed():
    """Test that Write to scratch/file.py is allowed"""
    result = test_hook("Write", {"file_path": f"{PROJECT_ROOT}/scratch/test_file.py"})

    assert result["hookSpecificOutput"]["permissionDecision"] == "allow", \
        "Should allow Write to scratch/file.py"
    print("✅ Allowed: Write scratch/test_file.py")


def test_archive_allowed():
    """Test that scratch/archive/ is allowed (exception)"""
    result = test_hook("Bash", {"command": "mkdir scratch/archive"})

    assert result["hookSpecificOutput"]["permissionDecision"] == "allow", \
        "Should allow mkdir scratch/archive (exception)"
    print("✅ Allowed: mkdir scratch/archive (exception)")


def test_archive_write_allowed():
    """Test that Write to scratch/archive/old.py is allowed"""
    result = test_hook("Write", {"file_path": f"{PROJECT_ROOT}/scratch/archive/old.py"})

    assert result["hookSpecificOutput"]["permissionDecision"] == "allow", \
        "Should allow Write to scratch/archive/ (exception)"
    print("✅ Allowed: Write scratch/archive/old.py (exception)")


def test_hidden_dir_allowed():
    """Test that scratch/.hidden/ is allowed"""
    result = test_hook("Bash", {"command": "mkdir scratch/.hidden"})

    assert result["hookSpecificOutput"]["permissionDecision"] == "allow", \
        "Should allow hidden directories"
    print("✅ Allowed: mkdir scratch/.hidden (hidden dir)")


def test_sudo_bypass():
    """Test that SUDO keyword bypasses enforcement"""
    result = test_hook("Bash", {"command": "mkdir scratch/temp"}, prompt="SUDO temp dir")

    assert result["hookSpecificOutput"]["permissionDecision"] == "allow", \
        "Should allow with SUDO bypass"
    print("✅ Allowed: mkdir scratch/temp (SUDO bypass)")


def test_non_scratch_allowed():
    """Test that non-scratch operations are allowed"""
    result = test_hook("Bash", {"command": "mkdir projects/myapp"})

    assert result["hookSpecificOutput"]["permissionDecision"] == "allow", \
        "Should allow operations outside scratch/"
    print("✅ Allowed: mkdir projects/myapp (not scratch)")


def test_read_operations_allowed():
    """Test that Read operations are not affected"""
    result = test_hook("Read", {"file_path": f"{PROJECT_ROOT}/scratch/nested/file.py"})

    assert result["hookSpecificOutput"]["permissionDecision"] == "allow", \
        "Read operations should not be blocked by this hook"
    print("✅ Allowed: Read operations not affected")


if __name__ == "__main__":
    tests = [
        test_mkdir_blocked,
        test_mkdir_p_blocked,
        test_write_nested_blocked,
        test_write_flat_allowed,
        test_archive_allowed,
        test_archive_write_allowed,
        test_hidden_dir_allowed,
        test_sudo_bypass,
        test_non_scratch_allowed,
        test_read_operations_allowed,
    ]

    print("Testing Scratch Flat Structure Enforcement Hook")
    print("=" * 50)

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {test.__name__}")
            print(f"   {e}")
            failed += 1
        except Exception as e:
            print(f"💥 ERROR: {test.__name__}")
            print(f"   {e}")
            failed += 1

    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")

    sys.exit(0 if failed == 0 else 1)
