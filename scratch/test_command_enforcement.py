#!/usr/bin/env python3
"""
Test Command Enforcement Hooks
Tests both command_tracker.py and command_prerequisite_gate.py
"""
import json
import subprocess
import sys
from pathlib import Path

# Paths
HOOKS_DIR = Path(__file__).resolve().parent.parent / ".claude" / "hooks"
TRACKER_HOOK = HOOKS_DIR / "command_tracker.py"
GATE_HOOK = HOOKS_DIR / "command_prerequisite_gate.py"

# Test session ID
TEST_SESSION = "test_cmd_enforcement"


def run_hook(hook_path, input_data):
    """Run a hook and return the output"""
    result = subprocess.run(
        ["python3", str(hook_path)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout) if result.stdout else {}


def test_command_tracker():
    """Test that command_tracker.py records command execution"""
    print("=" * 60)
    print("TEST 1: Command Tracker - Record /verify Execution")
    print("=" * 60)

    # Simulate PostToolUse event for /verify command
    input_data = {
        "sessionId": TEST_SESSION,
        "toolName": "Bash",
        "toolParams": {
            "command": 'python3 scripts/ops/verify.py command_success "pytest tests/"'
        },
    }

    output = run_hook(TRACKER_HOOK, input_data)
    print(f"Input: {json.dumps(input_data, indent=2)}")
    print(f"Output: {json.dumps(output, indent=2)}")

    # Check session state was updated
    sys.path.insert(
        0, str(Path(__file__).resolve().parent.parent / "scripts")
    )
    from lib.epistemology import load_session_state

    state = load_session_state(TEST_SESSION)

    if state and "commands_run" in state and "verify" in state["commands_run"]:
        print("✅ PASS: /verify command was recorded in session state")
        print(f"   State: {state['commands_run']}")
    else:
        print("❌ FAIL: /verify command was not recorded")
        sys.exit(1)

    print()


def test_prerequisite_gate_pass():
    """Test that prerequisite gate allows action when prerequisite met"""
    print("=" * 60)
    print("TEST 2: Prerequisite Gate - Allow with Met Prerequisite")
    print("=" * 60)

    # First, record that /verify was run (via tracker)
    # (Already done in test 1)

    # Now try to use Bash with "Fixed" in description
    # This should PASS because /verify was run in test 1 (turn 0)
    input_data = {
        "sessionId": TEST_SESSION,
        "toolName": "Bash",
        "toolParams": {
            "command": "echo 'Tests pass'",
            "description": "Tests are fixed",
        },
    }

    output = run_hook(GATE_HOOK, input_data)
    print(f"Input: {json.dumps(input_data, indent=2)}")
    print(f"Output: {json.dumps(output, indent=2)}")

    decision = output.get("hookSpecificOutput", {}).get("permissionDecision", "")

    if decision == "allow":
        print("✅ PASS: Action allowed when prerequisite met")
    else:
        print(f"❌ FAIL: Action blocked when prerequisite was met: {decision}")
        sys.exit(1)

    print()


def test_prerequisite_gate_block():
    """Test that prerequisite gate blocks action when prerequisite missing"""
    print("=" * 60)
    print("TEST 3: Prerequisite Gate - Block without Prerequisite")
    print("=" * 60)

    # Try to commit without running /upkeep
    # This should BLOCK because /upkeep was never run
    input_data = {
        "sessionId": TEST_SESSION,
        "toolName": "Bash",
        "toolParams": {"command": "git commit -m 'test'"},
    }

    output = run_hook(GATE_HOOK, input_data)
    print(f"Input: {json.dumps(input_data, indent=2)}")
    print(f"Output: {json.dumps(output, indent=2)}")

    decision = output.get("hookSpecificOutput", {}).get("permissionDecision", "")
    reason = output.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")

    if decision == "deny":
        print("✅ PASS: Action blocked when prerequisite missing")
        print(f"   Block reason: {reason[:100]}...")
    else:
        print(f"❌ FAIL: Action allowed when prerequisite missing: {decision}")
        sys.exit(1)

    print()


def test_read_before_edit():
    """Test that Edit requires Read first"""
    print("=" * 60)
    print("TEST 4: Read Before Edit - Block Edit without Read")
    print("=" * 60)

    # Try to edit a file that hasn't been read
    # This should BLOCK
    input_data = {
        "sessionId": TEST_SESSION,
        "toolName": "Edit",
        "toolParams": {
            "file_path": "/some/unread/file.py",
            "old_string": "foo",
            "new_string": "bar",
        },
    }

    output = run_hook(GATE_HOOK, input_data)
    print(f"Input: {json.dumps(input_data, indent=2)}")
    print(f"Output: {json.dumps(output, indent=2)}")

    decision = output.get("hookSpecificOutput", {}).get("permissionDecision", "")

    if decision == "deny":
        print("✅ PASS: Edit blocked when file not read first")
    else:
        print(f"❌ FAIL: Edit allowed without reading file: {decision}")
        sys.exit(1)

    print()


def test_production_write_requires_quality():
    """Test that Write to production code requires /audit and /void"""
    print("=" * 60)
    print("TEST 5: Production Write - Require Quality Gates")
    print("=" * 60)

    # Try to write production code without /audit or /void
    # This should BLOCK
    input_data = {
        "sessionId": TEST_SESSION,
        "toolName": "Write",
        "toolParams": {
            "file_path": "/path/to/scripts/ops/new_tool.py",
            "content": "print('hello')",
        },
    }

    output = run_hook(GATE_HOOK, input_data)
    print(f"Input: {json.dumps(input_data, indent=2)}")
    print(f"Output: {json.dumps(output, indent=2)}")

    decision = output.get("hookSpecificOutput", {}).get("permissionDecision", "")

    if decision == "deny":
        print("✅ PASS: Production write blocked without quality gates")
    else:
        print(f"❌ FAIL: Production write allowed without quality gates: {decision}")
        sys.exit(1)

    print()


def test_scratch_write_allowed():
    """Test that Write to scratch/ is allowed (no quality gates needed)"""
    print("=" * 60)
    print("TEST 6: Scratch Write - Allow without Quality Gates")
    print("=" * 60)

    # Try to write to scratch/ (should be allowed)
    input_data = {
        "sessionId": TEST_SESSION,
        "toolName": "Write",
        "toolParams": {
            "file_path": "/path/to/scratch/test.py",
            "content": "print('hello')",
        },
    }

    output = run_hook(GATE_HOOK, input_data)
    print(f"Input: {json.dumps(input_data, indent=2)}")
    print(f"Output: {json.dumps(output, indent=2)}")

    decision = output.get("hookSpecificOutput", {}).get("permissionDecision", "")

    if decision == "allow":
        print("✅ PASS: Scratch write allowed without quality gates")
    else:
        print(f"❌ FAIL: Scratch write blocked: {decision}")
        sys.exit(1)

    print()


def cleanup():
    """Clean up test session state"""
    print("=" * 60)
    print("CLEANUP: Removing Test Session State")
    print("=" * 60)

    state_file = (
        Path(__file__).resolve().parent.parent
        / ".claude"
        / "memory"
        / f"session_{TEST_SESSION}_state.json"
    )

    if state_file.exists():
        state_file.unlink()
        print(f"✅ Removed {state_file}")
    else:
        print(f"⚠️  No state file to remove")

    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("COMMAND ENFORCEMENT HOOKS TEST SUITE")
    print("=" * 60 + "\n")

    try:
        test_command_tracker()
        test_prerequisite_gate_pass()
        test_prerequisite_gate_block()
        test_read_before_edit()
        test_production_write_requires_quality()
        test_scratch_write_allowed()

        print("=" * 60)
        print("ALL TESTS PASSED ✅")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        cleanup()
