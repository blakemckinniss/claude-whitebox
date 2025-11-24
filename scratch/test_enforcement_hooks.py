#!/usr/bin/env python3
"""
Enforcement Hooks Test Suite
=============================
Tests the new anti-sycophancy enforcement hooks.
"""

import json
import subprocess
from pathlib import Path


def test_pre_advice_hook():
    """Test pre_advice.py blocks strategic questions at low confidence"""
    print("\n=== Testing pre_advice.py (Strategic Question Blocker) ===")

    test_cases = [
        ("Is this project ready for production?", True),
        ("Should we migrate to TypeScript?", True),
        ("What do you think about using GraphQL?", True),
        ("Can this be used as a template?", True),
        ("Add a new function to parse JSON", False),  # Not strategic
    ]

    for prompt, should_block in test_cases:
        result = subprocess.run(
            ["python3", ".claude/hooks/pre_advice.py"],
            input=prompt,
            capture_output=True,
            text=True
        )

        blocked = result.returncode != 0
        status = "✅" if blocked == should_block else "❌"
        action = "BLOCKED" if blocked else "ALLOWED"
        expected = "BLOCK" if should_block else "ALLOW"

        print(f"{status} '{prompt[:50]}...' - {action} (expected {expected})")

    return True


def test_absurdity_detector():
    """Test absurdity_detector.py flags contradictions"""
    print("\n=== Testing absurdity_detector.py (Contradiction Detector) ===")

    test_cases = [
        ("Install Rust in this JavaScript project", True),
        ("Use blockchain for user authentication", True),
        ("Add microservices for a simple todo app", True),
        ("Store passwords in plaintext", True),
        ("Add a REST endpoint for user registration", False),
    ]

    for prompt, should_warn in test_cases:
        result = subprocess.run(
            ["python3", ".claude/hooks/absurdity_detector.py"],
            input=prompt,
            capture_output=True,
            text=True
        )

        warned = "ABSURDITY DETECTOR TRIGGERED" in result.stderr
        status = "✅" if warned == should_warn else "❌"
        action = "WARNED" if warned else "PASSED"
        expected = "WARN" if should_warn else "PASS"

        print(f"{status} '{prompt[:50]}...' - {action} (expected {expected})")

    return True


def test_pre_delegation():
    """Test pre_delegation.py blocks advisor calls without context"""
    print("\n=== Testing pre_delegation.py (Delegation Validator) ===")

    test_cases = [
        ("python3 scripts/ops/council.py \"Should we use X?\"", "council.py", True),
        ("python3 scripts/ops/critic.py \"Idea: use Y\"", "critic.py", True),
        ("python3 scripts/ops/judge.py \"Migrate to Z\"", "judge.py", True),
        ("ls -la", None, False),  # Not an advisor
        ("git status", None, False),
    ]

    for command, advisor, should_block in test_cases:
        input_data = {
            "toolName": "Bash",
            "toolParams": {"command": command}
        }

        result = subprocess.run(
            ["python3", ".claude/hooks/pre_delegation.py"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        try:
            output = json.loads(result.stdout)
            blocked = output["hookSpecificOutput"]["action"] == "deny"
        except:
            blocked = False

        status = "✅" if blocked == should_block else "❌"
        action = "BLOCKED" if blocked else "ALLOWED"
        expected = "BLOCK" if should_block else "ALLOW"

        cmd_short = command[:40] + "..." if len(command) > 40 else command
        print(f"{status} '{cmd_short}' - {action} (expected {expected})")

    return True


def test_confidence_gate():
    """Test confidence_gate.py blocks production writes at low confidence"""
    print("\n=== Testing confidence_gate.py (Production Write Blocker) ===")

    test_cases = [
        ("scripts/ops/new_tool.py", True),  # Production file
        (".claude/hooks/new_hook.py", True),
        ("scratch/test.py", False),  # Scratch allowed
    ]

    for file_path, should_block in test_cases:
        input_data = {
            "toolName": "Write",
            "toolParams": {"file_path": file_path, "content": "test"}
        }

        result = subprocess.run(
            ["python3", ".claude/hooks/confidence_gate.py"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True
        )

        try:
            output = json.loads(result.stdout)
            blocked = output["hookSpecificOutput"]["action"] == "deny"
        except:
            blocked = False

        status = "✅" if blocked == should_block else "❌"
        action = "BLOCKED" if blocked else "ALLOWED"
        expected = "BLOCK" if should_block else "ALLOW"

        print(f"{status} Write to '{file_path}' - {action} (expected {expected})")

    return True


def main():
    print("=" * 70)
    print("ENFORCEMENT HOOKS TEST SUITE")
    print("=" * 70)
    print("\nTesting with confidence at 0% (worst case)\n")

    results = []

    try:
        results.append(("pre_advice", test_pre_advice_hook()))
    except Exception as e:
        print(f"❌ pre_advice test failed: {e}")
        results.append(("pre_advice", False))

    try:
        results.append(("absurdity_detector", test_absurdity_detector()))
    except Exception as e:
        print(f"❌ absurdity_detector test failed: {e}")
        results.append(("absurdity_detector", False))

    try:
        results.append(("pre_delegation", test_pre_delegation()))
    except Exception as e:
        print(f"❌ pre_delegation test failed: {e}")
        results.append(("pre_delegation", False))

    try:
        results.append(("confidence_gate", test_confidence_gate()))
    except Exception as e:
        print(f"❌ confidence_gate test failed: {e}")
        results.append(("confidence_gate", False))

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")

    all_passed = all(p for _, p in results)

    print("\n" + ("🎉 ALL TESTS PASSED" if all_passed else "⚠️  SOME TESTS FAILED"))

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
