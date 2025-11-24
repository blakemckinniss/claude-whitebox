#!/usr/bin/env python3
"""Test deny cases for hooks"""
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
            return True, None, result.returncode

    except Exception as e:
        return False, str(e), -1

print("Testing Deny Cases\n" + "="*50)

# Test ban_stubs.py with stub code
print("\nTest: ban_stubs.py - deny stub code")
stub_input = {
    "sessionId": "test123",
    "toolName": "Write",
    "toolParams": {
        "file_path": "/tmp/test.py",
        "content": "def foo():\n    # TODO: implement this\n    pass\n"
    }
}

success, output, exit_code = test_hook(".claude/hooks/ban_stubs.py", stub_input)

if not success:
    print(f"  ❌ FAILED: {output}")
elif output is None:
    print(f"  ❌ FAILED: Expected output, got none")
else:
    # Verify deny structure
    if 'hookSpecificOutput' not in output:
        print(f"  ❌ FAILED: Missing hookSpecificOutput wrapper")
        print(f"     Got: {json.dumps(output, indent=2)}")
    else:
        inner = output['hookSpecificOutput']
        if inner.get('permissionDecision') == 'deny':
            if 'permissionDecisionReason' in inner:
                print(f"  ✅ PASSED: Correctly denies stub code")
                print(f"     Decision: {inner['permissionDecision']}")
                print(f"     Reason preview: {inner['permissionDecisionReason'][:80]}...")
            else:
                print(f"  ❌ FAILED: Missing permissionDecisionReason")
        else:
            print(f"  ❌ FAILED: Expected deny, got {inner.get('permissionDecision')}")

# Test risk_gate.py with dangerous command
print("\nTest: risk_gate.py - deny dangerous command")
danger_input = {
    "sessionId": "test123",
    "toolName": "Bash",
    "toolParams": {"command": "rm -rf /"}
}

success, output, exit_code = test_hook(".claude/hooks/risk_gate.py", danger_input)

if not success:
    print(f"  ❌ FAILED: {output}")
elif output is None:
    print(f"  ❌ FAILED: Expected output, got none")
else:
    if 'hookSpecificOutput' not in output:
        print(f"  ❌ FAILED: Missing hookSpecificOutput wrapper")
    else:
        inner = output['hookSpecificOutput']
        if inner.get('permissionDecision') == 'deny':
            if 'permissionDecisionReason' in inner:
                print(f"  ✅ PASSED: Correctly denies dangerous command")
                print(f"     Decision: {inner['permissionDecision']}")
                print(f"     Reason preview: {inner['permissionDecisionReason'][:80]}...")
            else:
                print(f"  ❌ FAILED: Missing permissionDecisionReason")
        else:
            print(f"  ❌ FAILED: Expected deny, got {inner.get('permissionDecision')}")

print("\n" + "="*50)
print("✅ Deny case tests complete!")
