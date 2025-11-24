#!/usr/bin/env python3
"""
Integration tests for organizational drift hooks
Tests actual hook behavior via subprocess calls
"""

import json
import subprocess
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
hook_path = repo_root / ".claude" / "hooks" / "org_drift_gate.py"


def create_hook_input(tool_name: str, file_path: str, sudo: bool = False) -> dict:
    """Create hook input JSON"""
    return {
        "toolName": tool_name,
        "toolParams": {"file_path": file_path},
        "messages": [
            {"content": "SUDO test prompt" if sudo else "test prompt"}
        ]
    }


def run_hook(tool_name: str, file_path: str, sudo: bool = False) -> dict:
    """Run the hook and return JSON response"""
    hook_input = create_hook_input(tool_name, file_path, sudo)

    result = subprocess.run(
        ["python3", str(hook_path)],
        input=json.dumps(hook_input),
        capture_output=True,
        text=True
    )

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Failed to parse hook output: {result.stdout}")
        print(f"Stderr: {result.stderr}")
        raise


def test_recursion_blocks():
    """Test that recursive paths are blocked"""
    print("Testing recursion blocking...")

    response = run_hook("Write", "scripts/scripts/ops/test.py")

    assert response["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "Recursive" in response["hookSpecificOutput"]["permissionDecisionReason"]

    print("✅ Recursion blocked correctly")


def test_root_pollution_blocks():
    """Test that root pollution is blocked"""
    print("Testing root pollution blocking...")

    response = run_hook("Write", str(repo_root / "test_file.py"))

    assert response["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "Root pollution" in response["hookSpecificOutput"]["permissionDecisionReason"]

    print("✅ Root pollution blocked correctly")


def test_production_pollution_blocks():
    """Test that test files in production zones are blocked"""
    print("Testing production pollution blocking...")

    response = run_hook("Write", "scripts/ops/test_audit.py")

    assert response["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "Production zone pollution" in response["hookSpecificOutput"]["permissionDecisionReason"]

    print("✅ Production pollution blocked correctly")


def test_valid_file_allowed():
    """Test that valid files are allowed"""
    print("Testing valid file allowed...")

    response = run_hook("Write", "scratch/my_script.py")

    assert response["hookSpecificOutput"]["permissionDecision"] == "allow"

    print("✅ Valid file allowed correctly")


def test_sudo_override():
    """Test that SUDO keyword overrides blocks"""
    print("Testing SUDO override...")

    # Should block without SUDO
    response1 = run_hook("Write", str(repo_root / "test.py"), sudo=False)
    assert response1["hookSpecificOutput"]["permissionDecision"] == "deny"

    # Should allow with SUDO
    response2 = run_hook("Write", str(repo_root / "test.py"), sudo=True)
    assert response2["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert "SUDO override" in response2["hookSpecificOutput"]["permissionDecisionReason"]

    print("✅ SUDO override working correctly")


def test_warnings_dont_block():
    """Test that warnings are shown but don't block operations"""
    print("Testing warnings don't block...")

    # This should potentially trigger warnings but still allow
    response = run_hook("Write", "scripts/ops/new_tool.py")

    # Should be allowed (no errors)
    assert response["hookSpecificOutput"]["permissionDecision"] == "allow"

    # Might have warnings (we won't assert this as it depends on system state)

    print("✅ Warnings don't block operations")


def test_excluded_paths_bypass():
    """Test that excluded paths bypass all checks"""
    print("Testing excluded paths bypass...")

    # node_modules should be excluded
    response = run_hook("Write", "node_modules/test.py")
    assert response["hookSpecificOutput"]["permissionDecision"] == "allow"

    # projects/ should be excluded
    response = run_hook("Write", "projects/myapp/test.py")
    assert response["hookSpecificOutput"]["permissionDecision"] == "allow"

    print("✅ Excluded paths bypass checks")


def test_edit_also_checked():
    """Test that Edit operations are also checked"""
    print("Testing Edit operations...")

    response = run_hook("Edit", "scripts/scripts/ops/test.py")

    assert response["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "Recursive" in response["hookSpecificOutput"]["permissionDecisionReason"]

    print("✅ Edit operations checked correctly")


def run_integration_tests():
    """Run all integration tests"""
    print("=" * 60)
    print("ORGANIZATIONAL DRIFT HOOKS - INTEGRATION TEST SUITE")
    print("=" * 60)
    print()

    tests = [
        test_recursion_blocks,
        test_root_pollution_blocks,
        test_production_pollution_blocks,
        test_valid_file_allowed,
        test_sudo_override,
        test_warnings_dont_block,
        test_excluded_paths_bypass,
        test_edit_also_checked,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"💥 {test.__name__} ERROR: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_integration_tests())
