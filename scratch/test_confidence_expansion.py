#!/usr/bin/env python3
"""
Test script for expanded confidence system
Validates new gains/penalties for engineering best practices
"""
import sys
from pathlib import Path

# Add scripts/lib to path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.epistemology import (
    CONFIDENCE_GAINS,
    CONFIDENCE_PENALTIES,
    _detect_git_operation,
    _detect_documentation_read,
    _detect_test_file_operation,
    update_confidence,
    check_tier_gate,
    initialize_session_state,
    load_session_state,
    save_session_state,
)

def test_confidence_gains():
    """Test that all new confidence gains are present"""
    print("=== Testing Confidence Gains ===\n")

    required_gains = {
        # Git operations
        "git_commit": 10,
        "git_status": 5,
        "git_log": 5,
        "git_diff": 10,
        "git_add": 5,
        # Documentation reading
        "read_md_first": 15,
        "read_md_repeat": 5,
        "read_claude_md": 20,
        "read_readme": 15,
        # Technical debt cleanup
        "fix_todo": 10,
        "remove_stub": 15,
        "reduce_complexity": 10,
        # Testing
        "write_tests": 15,
        "add_test_coverage": 20,
    }

    all_present = True
    for key, expected_value in required_gains.items():
        if key not in CONFIDENCE_GAINS:
            print(f"❌ MISSING: {key}")
            all_present = False
        elif CONFIDENCE_GAINS[key] != expected_value:
            print(f"⚠️  MISMATCH: {key} = {CONFIDENCE_GAINS[key]} (expected {expected_value})")
            all_present = False
        else:
            print(f"✅ {key}: +{CONFIDENCE_GAINS[key]}%")

    print()
    return all_present


def test_confidence_penalties():
    """Test that all new confidence penalties are present"""
    print("=== Testing Confidence Penalties ===\n")

    required_penalties = {
        # Context blindness
        "edit_before_read": -20,
        "modify_unexamined": -25,
        # User context ignorance
        "repeat_instruction": -15,
        # Testing negligence
        "skip_test_easy": -15,
        "claim_done_no_test": -20,
        # Security/quality shortcuts
        "modify_no_audit": -25,
        "commit_no_upkeep": -15,
        "write_stub": -10,
    }

    all_present = True
    for key, expected_value in required_penalties.items():
        if key not in CONFIDENCE_PENALTIES:
            print(f"❌ MISSING: {key}")
            all_present = False
        elif CONFIDENCE_PENALTIES[key] != expected_value:
            print(f"⚠️  MISMATCH: {key} = {CONFIDENCE_PENALTIES[key]} (expected {expected_value})")
            all_present = False
        else:
            print(f"✅ {key}: {CONFIDENCE_PENALTIES[key]}%")

    print()
    return all_present


def test_git_detection():
    """Test git operation detection"""
    print("=== Testing Git Operation Detection ===\n")

    test_cases = [
        ("git commit -m 'test'", "git_commit", 10),
        ("git status", "git_status", 5),
        ("git diff HEAD", "git_diff", 10),
        ("git log --oneline", "git_log", 5),
        ("git add .", "git_add", 5),
        ("ls -la", None, 0),  # Should not match
        ("pytest tests/", None, 0),  # Should not match
    ]

    all_passed = True
    for command, expected_key, expected_boost in test_cases:
        key, boost = _detect_git_operation(command)
        if key == expected_key and boost == expected_boost:
            status = "✅"
        else:
            status = "❌"
            all_passed = False
        print(f"{status} '{command[:30]:30}' -> {key or 'None':15} (+{boost}%)")

    print()
    return all_passed


def test_documentation_detection():
    """Test documentation reading detection"""
    print("=== Testing Documentation Read Detection ===\n")

    test_cases = [
        ("CLAUDE.md", {}, "read_claude_md", 20),
        ("README.md", {}, "read_readme", 15),
        ("docs/guide.md", {}, "read_md_first", 15),
        ("docs/guide.md", {"docs/guide.md": 1}, "read_md_repeat", 5),  # Already read
        ("src/main.py", {}, None, 0),  # Not .md file
    ]

    all_passed = True
    for file_path, read_files, expected_key, expected_boost in test_cases:
        key, boost = _detect_documentation_read(file_path, read_files)
        if key == expected_key and boost == expected_boost:
            status = "✅"
        else:
            status = "❌"
            all_passed = False
        repeat = " (repeat)" if read_files else ""
        print(f"{status} {file_path:30}{repeat:10} -> {key or 'None':15} (+{boost}%)")

    print()
    return all_passed


def test_test_file_detection():
    """Test test file operation detection"""
    print("=== Testing Test File Detection ===\n")

    test_cases = [
        ("test_auth.py", "Write", "write_tests", 15),
        ("test_auth.py", "Edit", "add_test_coverage", 20),
        ("tests/test_api.py", "Write", "write_tests", 15),
        ("tests/test_api.py", "Edit", "add_test_coverage", 20),
        ("auth_test.py", "Write", "write_tests", 15),
        ("src/auth.py", "Write", None, 0),  # Not a test file
        ("src/auth.py", "Edit", None, 0),  # Not a test file
    ]

    all_passed = True
    for file_path, operation, expected_key, expected_boost in test_cases:
        key, boost = _detect_test_file_operation(file_path, operation)
        if key == expected_key and boost == expected_boost:
            status = "✅"
        else:
            status = "❌"
            all_passed = False
        print(f"{status} {file_path:30} ({operation:5}) -> {key or 'None':20} (+{boost}%)")

    print()
    return all_passed


def test_update_confidence_integration():
    """Test that update_confidence() integrates new detection"""
    print("=== Testing update_confidence() Integration ===\n")

    # Create test session
    session_id = "test_expansion"
    state = initialize_session_state(session_id)

    test_cases = [
        # Git operations
        ("Bash", {"command": "git status"}, 5, "git status"),
        ("Bash", {"command": "git commit -m 'test'"}, 10, "git commit"),
        ("Bash", {"command": "git diff HEAD"}, 10, "git diff"),

        # Documentation reading
        ("Read", {"file_path": "CLAUDE.md"}, 20, "CLAUDE.md first read"),
        ("Read", {"file_path": "CLAUDE.md"}, 5, "CLAUDE.md re-read"),
        ("Read", {"file_path": "README.md"}, 15, "README.md first read"),
        ("Read", {"file_path": "docs/api.md"}, 15, "generic .md first read"),

        # Test file operations
        ("Write", {"file_path": "test_new.py"}, 15, "write test file"),
        ("Edit", {"file_path": "test_existing.py"}, 20, "edit test file"),

        # Regular operations (should still work)
        ("Read", {"file_path": "src/main.py"}, 10, "regular file first read"),
        ("Read", {"file_path": "src/main.py"}, 2, "regular file re-read"),
    ]

    all_passed = True
    for tool_name, tool_input, expected_boost, description in test_cases:
        old_confidence = state["confidence"]
        new_confidence, boost = update_confidence(
            session_id=session_id,
            tool_name=tool_name,
            tool_input=tool_input,
            turn=state["turn_count"],
            reason=description,
        )

        # Reload state to see changes
        state = load_session_state(session_id)

        if boost == expected_boost:
            status = "✅"
        else:
            status = "❌"
            all_passed = False

        print(f"{status} {description:30} -> +{boost}% (expected +{expected_boost}%)")

    print()
    return all_passed


def test_tier_gate_penalties():
    """Test that tier_gate applies correct penalties"""
    print("=== Testing Tier Gate Penalties ===\n")

    # Create test session with 71% confidence (Certainty tier)
    session_id = "test_tier_gate"
    state = initialize_session_state(session_id)
    state["confidence"] = 71
    save_session_state(session_id, state)

    test_cases = [
        # Edit before read - should apply edit_before_read penalty (-20%)
        ("Edit", {"file_path": "/tmp/never_read.py"}, False, "edit_before_read", "Edit unread file"),

        # Edit after read - should allow
        # (We'll add file to read_files first)
    ]

    all_passed = True
    for tool_name, tool_input, should_allow, expected_penalty, description in test_cases:
        allowed, message, penalty_type = check_tier_gate(
            tool_name, tool_input, state["confidence"], session_id
        )

        if allowed == should_allow and (not should_allow and penalty_type == expected_penalty):
            status = "✅"
        else:
            status = "❌"
            all_passed = False

        print(f"{status} {description:30} -> Allowed: {allowed}, Penalty: {penalty_type or 'None'}")

    # Test Edit after read - should allow
    state = load_session_state(session_id)
    state["read_files"] = {"/tmp/already_read.py": 1}
    state["confidence"] = 71
    save_session_state(session_id, state)

    allowed, message, penalty_type = check_tier_gate(
        "Edit", {"file_path": "/tmp/already_read.py"}, 71, session_id
    )

    if allowed and penalty_type is None:
        status = "✅"
    else:
        status = "❌"
        all_passed = False

    print(f"{status} {'Edit read file':30} -> Allowed: {allowed}, Penalty: {penalty_type or 'None'}")

    print()
    return all_passed


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("CONFIDENCE SYSTEM EXPANSION TEST SUITE")
    print("=" * 60 + "\n")

    results = []

    results.append(("Confidence Gains", test_confidence_gains()))
    results.append(("Confidence Penalties", test_confidence_penalties()))
    results.append(("Git Detection", test_git_detection()))
    results.append(("Documentation Detection", test_documentation_detection()))
    results.append(("Test File Detection", test_test_file_detection()))
    results.append(("update_confidence() Integration", test_update_confidence_integration()))
    results.append(("Tier Gate Penalties", test_tier_gate_penalties()))

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60 + "\n")

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:10} {test_name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("✅ ALL TESTS PASSED")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
