#!/usr/bin/env python3
"""
Test script to verify hook JSON output format matches official docs
"""
import json
import subprocess
import sys

def test_hook(hook_path, test_input):
    """Test a hook with given input and verify JSON output"""
    try:
        result = subprocess.run(
            ["python3", hook_path],
            input=json.dumps(test_input),
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.stdout:
            try:
                output = json.loads(result.stdout)
                return True, output, result.returncode
            except json.JSONDecodeError as e:
                return False, f"Invalid JSON: {e}", result.returncode
        else:
            return True, None, result.returncode  # No output is valid

    except Exception as e:
        return False, str(e), -1

# Test cases
test_cases = [
    {
        "name": "tier_gate.py - allow",
        "hook": ".claude/hooks/tier_gate.py",
        "input": {
            "sessionId": "test123",
            "toolName": "Read",
            "toolParams": {"file_path": "/tmp/test.txt"}
        },
        "expected_structure": {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow"
            }
        }
    },
    {
        "name": "risk_gate.py - allow safe command",
        "hook": ".claude/hooks/risk_gate.py",
        "input": {
            "sessionId": "test123",
            "toolName": "Bash",
            "toolParams": {"command": "ls -la"}
        },
        "expected_structure": {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow"
            }
        }
    },
    {
        "name": "ban_stubs.py - allow non-Write",
        "hook": ".claude/hooks/ban_stubs.py",
        "input": {
            "sessionId": "test123",
            "toolName": "Read",
            "toolParams": {}
        },
        "expected_structure": {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow"
            }
        }
    }
]

print("Testing Hook JSON Output Format\n" + "="*50)

all_passed = True
for test in test_cases:
    print(f"\nTest: {test['name']}")
    success, output, exit_code = test_hook(test['hook'], test['input'])

    if not success:
        print(f"  ❌ FAILED: {output}")
        all_passed = False
        continue

    if output is None:
        print(f"  ✅ PASSED: No output (exit code {exit_code})")
        continue

    # Verify structure
    expected = test['expected_structure']
    if 'hookSpecificOutput' in expected:
        if 'hookSpecificOutput' not in output:
            print(f"  ❌ FAILED: Missing 'hookSpecificOutput' wrapper")
            print(f"     Got: {json.dumps(output, indent=2)}")
            all_passed = False
            continue

        inner = output['hookSpecificOutput']
        expected_inner = expected['hookSpecificOutput']

        for key, value in expected_inner.items():
            if key not in inner:
                print(f"  ❌ FAILED: Missing key '{key}' in hookSpecificOutput")
                all_passed = False
                continue
            if inner[key] != value:
                print(f"  ❌ FAILED: {key}={inner[key]}, expected {value}")
                all_passed = False
                continue

    print(f"  ✅ PASSED: Valid JSON with correct structure")
    print(f"     Output: {json.dumps(output, indent=2)}")

print("\n" + "="*50)
if all_passed:
    print("✅ All tests passed!")
    sys.exit(0)
else:
    print("❌ Some tests failed")
    sys.exit(1)
