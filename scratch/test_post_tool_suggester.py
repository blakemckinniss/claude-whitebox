#!/usr/bin/env python3
"""Test the PostToolUse command suggester hook"""
import json
import subprocess
import sys
from pathlib import Path

# Test scenarios
test_cases = [
    {
        "name": "Write to Production Code",
        "input": {
            "sessionId": "test-session",
            "toolName": "Write",
            "toolParams": {"file_path": "/home/user/project/scripts/ops/new_tool.py"},
            "toolResult": "File written successfully"
        },
        "expected_keywords": ["QUALITY GATES", "/audit", "/void", "/drift"]
    },
    {
        "name": "Completion Claim in Result",
        "input": {
            "sessionId": "test-session",
            "toolName": "Bash",
            "toolParams": {"command": "python3 setup.py install"},
            "toolResult": "Installation complete. All tests passed successfully."
        },
        "expected_keywords": ["COMPLETION CLAIM", "/void", "/verify"]
    },
    {
        "name": "Test Command Execution",
        "input": {
            "sessionId": "test-session",
            "toolName": "Bash",
            "toolParams": {"command": "pytest tests/test_auth.py"},
            "toolResult": "===== 5 passed in 0.23s ====="
        },
        "expected_keywords": ["TEST COMMAND", "/verify", "exit code"]
    },
    {
        "name": "Web API Research",
        "input": {
            "sessionId": "test-session",
            "toolName": "WebSearch",
            "toolParams": {"query": "FastAPI dependency injection API documentation"},
            "toolResult": "Results found..."
        },
        "expected_keywords": ["API RESEARCH", "/probe", "runtime"]
    },
    {
        "name": "Error in Result",
        "input": {
            "sessionId": "test-session",
            "toolName": "Bash",
            "toolParams": {"command": "npm install broken-pkg"},
            "toolResult": "Error: Package not found. Failed to install."
        },
        "expected_keywords": ["ERROR DETECTED", "/verify", "VERIFICATION LOOP"]
    },
    {
        "name": "Agent Delegation",
        "input": {
            "sessionId": "test-session",
            "toolName": "Task",
            "toolParams": {"subagent_type": "researcher", "prompt": "Research Playwright"},
            "toolResult": "Agent completed successfully"
        },
        "expected_keywords": ["AGENT DELEGATION", "/evidence", "/confidence"]
    },
    {
        "name": "No Pattern Match (should be silent)",
        "input": {
            "sessionId": "test-session",
            "toolName": "Read",
            "toolParams": {"file_path": "/home/user/project/README.md"},
            "toolResult": "File contents..."
        },
        "expected_keywords": []  # Should produce no suggestions
    }
]

hook_path = Path(__file__).parent / "post_tool_command_suggester.py"

print("Testing PostToolUse Command Suggester Hook")
print("=" * 60)

passed = 0
failed = 0

for test in test_cases:
    print(f"\nTest: {test['name']}")
    print("-" * 60)

    # Run hook with test input
    result = subprocess.run(
        ["python3", str(hook_path)],
        input=json.dumps(test["input"]),
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"❌ FAILED: Hook exited with code {result.returncode}")
        print(f"stderr: {result.stderr}")
        failed += 1
        continue

    try:
        output = json.loads(result.stdout)
        context = output.get("hookSpecificOutput", {}).get("additionalContext", "")

        # Check if expected keywords are present
        if test["expected_keywords"]:
            all_found = all(kw in context for kw in test["expected_keywords"])

            if all_found:
                print(f"✅ PASSED: All keywords found")
                print(f"Output preview: {context[:200]}...")
                passed += 1
            else:
                print(f"❌ FAILED: Missing expected keywords")
                print(f"Expected: {test['expected_keywords']}")
                print(f"Got: {context[:300]}")
                failed += 1
        else:
            # Should be silent (no suggestions)
            if context.strip() == "":
                print(f"✅ PASSED: Correctly silent (no pattern match)")
                passed += 1
            else:
                print(f"❌ FAILED: Should be silent but produced output")
                print(f"Got: {context}")
                failed += 1

    except json.JSONDecodeError as e:
        print(f"❌ FAILED: Invalid JSON output")
        print(f"stdout: {result.stdout}")
        print(f"error: {e}")
        failed += 1

print("\n" + "=" * 60)
print(f"Results: {passed} passed, {failed} failed")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
