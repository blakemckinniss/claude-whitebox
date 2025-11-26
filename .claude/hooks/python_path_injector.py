#!/usr/bin/env python3
"""
Python Path Enforcer: PreToolUse hook that rejects bare python/pip commands.

Forces use of .claude/.venv/bin/python instead of system python.
"""

import sys
import json
import os
import re

def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({}))
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name != "Bash":
        print(json.dumps({}))
        sys.exit(0)

    command = tool_input.get("command", "")

    # Pattern: bare python/pip at start or after shell operators
    bare_python = re.search(r'(^|&&|\|\||;|\|)\s*(python3?|pip3?)\s', command)

    # Allow if already using venv path
    if bare_python and ".venv/bin" not in command:
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
        venv_bin = f"{project_dir}/.claude/.venv/bin"

        result = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Use venv: {venv_bin}/python or {venv_bin}/pip"
            }
        }
        print(json.dumps(result))
        sys.exit(0)

    print(json.dumps({}))
    sys.exit(0)

if __name__ == "__main__":
    main()
