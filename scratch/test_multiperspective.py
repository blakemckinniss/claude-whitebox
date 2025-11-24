#!/usr/bin/env python3
"""
Multi-Perspective Enforcement Test
===================================
Tests that pre_delegation.py blocks single-advisor strategic decisions
and requires FOR/AGAINST/NEUTRAL consultation.
"""

import json
import subprocess


def test_delegation_hook(command, expected_action, description):
    """Test pre_delegation.py hook with a bash command"""
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
        action = output["hookSpecificOutput"]["action"]
    except:
        action = "error"

    passed = action == expected_action
    status = "✅" if passed else "❌"
    print(f"{status} {description}")
    print(f"   Command: {command[:60]}...")
    print(f"   Expected: {expected_action}, Got: {action}")

    if not passed and "denyReason" in output.get("hookSpecificOutput", {}):
        print(f"   Reason: {output['hookSpecificOutput']['denyReason'][:200]}...")

    print()
    return passed


def main():
    print("="*70)
    print("MULTI-PERSPECTIVE ENFORCEMENT TESTS")
    print("="*70)
    print()

    # Reset confidence to sufficient level for these tests
    import json
    from pathlib import Path

    state_file = Path('.claude/memory/confidence_state.json')
    with open(state_file) as f:
        state = json.load(f)
    state['confidence'] = 50  # Above delegation threshold (40%)
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)

    print(f"Confidence set to 50% for testing (above 40% threshold)\n")

    tests = [
        # Strategic decisions + single advisor → BLOCKED
        (
            'python3 scripts/ops/critic.py "Should we migrate to GraphQL?"',
            "deny",
            "Strategic decision to single advisor (critic) - SHOULD BLOCK"
        ),
        (
            'python3 scripts/ops/judge.py "Is this architecture ready for production?"',
            "deny",
            "Strategic decision to single advisor (judge) - SHOULD BLOCK"
        ),
        (
            'python3 scripts/ops/skeptic.py "Should we use microservices?"',
            "deny",
            "Strategic decision to single advisor (skeptic) - SHOULD BLOCK"
        ),

        # Strategic decisions + council → ALLOWED
        (
            'python3 scripts/ops/council.py "Should we migrate to GraphQL?"',
            "allow",
            "Strategic decision to council (multi-perspective) - SHOULD ALLOW"
        ),
        (
            'python3 scripts/ops/balanced_council.py "Use microservices"',
            "allow",
            "Strategic decision to balanced_council (FOR/AGAINST/NEUTRAL) - SHOULD ALLOW"
        ),

        # Non-strategic + single advisor → ALLOWED
        (
            'python3 scripts/ops/think.py "How to implement user authentication"',
            "allow",
            "Non-strategic question to think - SHOULD ALLOW"
        ),
        (
            'python3 scripts/ops/consult.py "What are best practices for error handling?"',
            "allow",
            "Non-strategic question to consult - SHOULD ALLOW"
        ),

        # Non-advisor commands → ALLOWED
        (
            'git status',
            "allow",
            "Non-advisor bash command - SHOULD ALLOW"
        ),
    ]

    results = []
    for command, expected, desc in tests:
        passed = test_delegation_hook(command, expected, desc)
        results.append(passed)

    # Reset confidence
    state['confidence'] = 0
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)

    print("="*70)
    print("RESULTS")
    print("="*70)
    passed_count = sum(results)
    total_count = len(results)
    print(f"{passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED - Multi-perspective enforcement working!")
    else:
        print(f"\n⚠️  {total_count - passed_count} tests failed")

    return 0 if passed_count == total_count else 1


if __name__ == "__main__":
    exit(main())
