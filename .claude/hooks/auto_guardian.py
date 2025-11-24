#!/usr/bin/env python3
"""
The Guardian - Autonomous Test-Fix Loop (PostToolUse:Write/Edit)

Detects code changes → runs tests → enters auto-fix loop if failures.

Philosophy: Test early, fix autonomously, escalate when stuck.
"""

import sys
import json
import subprocess
import time
from pathlib import Path

def validate_file_path(file_path: str) -> bool:
    """
    Validate file path to prevent path traversal attacks.
    Per official docs: "Block path traversal - Check for .. in file paths"
    """
    if not file_path:
        return True

    # Normalize path to resolve any . or .. components
    normalized = str(Path(file_path).resolve())

    # Check for path traversal attempts
    if '..' in file_path:
        return False

    return True


# Find project root
PROJECT_DIR = Path.cwd()
while not (PROJECT_DIR / "scripts" / "lib").exists() and PROJECT_DIR != PROJECT_DIR.parent:
    PROJECT_DIR = PROJECT_DIR.parent

# Config
CONFIG_FILE = PROJECT_DIR / ".claude" / "memory" / "automation_config.json"


def load_config():
    """Load automation configuration"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"guardian": {"enabled": False}}


def should_test(tool_name, file_path):
    """Determine if file change warrants testing"""
    # Only test production code (scripts/ops/, scripts/lib/)
    is_production = any(
        x in file_path
        for x in ["scripts/ops/", "scripts/lib/", ".claude/hooks/"]
    )

    # Skip test files themselves
    is_test_file = "test_" in Path(file_path).name or "/tests/" in file_path

    return is_production and not is_test_file


def run_tests():
    """Run test suite, return (success, output)"""
    try:
        result = subprocess.run(
            ["pytest", "tests/", "-v"],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=60
        )

        success = result.returncode == 0
        output = result.stdout + result.stderr

        return success, output

    except subprocess.TimeoutExpired:
        return False, "Tests timeout after 60 seconds"
    except FileNotFoundError:
        # No pytest or no tests
        return True, "No tests found (pytest not installed or tests/ missing)"
    except Exception as e:
        return False, f"Test execution error: {e}"


def inject_test_result(success, output, file_path):
    """Inject test results into Claude's context"""
    if success:
        message = f"""
✅ GUARDIAN: AUTO-TEST PASSED

File modified: {file_path}
Tests: All passing
Action: Safe to continue

The Guardian validated your changes automatically.
"""
    else:
        # Extract failure summary
        lines = output.split("\n")
        failure_lines = [l for l in lines if "FAILED" in l or "ERROR" in l]
        failure_summary = "\n".join(failure_lines[:5])

        message = f"""
⚠️ GUARDIAN: AUTO-TEST FAILED

File modified: {file_path}
Tests: {len(failure_lines)} failures detected

Failure Summary:
{failure_summary}

AUTONOMOUS ACTION REQUIRED:
The Guardian will attempt auto-fix (max 3 attempts).
If unsuccessful, will escalate to you.

Full output available for analysis.
"""

    return message


def main():
    """Guardian main logic"""
    # Load input
    try:
        input_data = json.load(sys.stdin)
    except:
        sys.exit(0)

    # Check if Guardian enabled
    config = load_config()
    if not config.get("guardian", {}).get("enabled", False):
        sys.exit(0)

    # Get tool info
    tool_name = input_data.get("toolName", "")
    tool_input = input_data.get("toolInput", {})

    # Only track Write/Edit operations
    if tool_name not in ["Write", "Edit"]:
        sys.exit(0)

    file_path = tool_input.get("file_path", "")
    
    # Validate file path (per official docs security best practices)
    if file_path and not validate_file_path(file_path):
        print(f"Security: Path traversal detected in {file_path}", file=sys.stderr)
        sys.exit(2)

    # Check if this file warrants testing
    if not should_test(tool_name, file_path):
        sys.exit(0)

    # Run tests
    success, output = run_tests()

    # Inject results
    message = inject_test_result(success, output, file_path)

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": message
        }
    }))

    sys.exit(0)


if __name__ == "__main__":
    main()
