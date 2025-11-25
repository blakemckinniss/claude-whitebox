#!/usr/bin/env python3
"""Block MCP tools - forces whitebox approach"""
import sys
import json

try:
    input_data = json.load(sys.stdin)
except (json.JSONDecodeError, ValueError):
    sys.exit(0)

tool_name = input_data.get("toolName", "Unknown")

# The JSON response that forces the block
output = {
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            f"⛔ SYSTEM POLICY: External MCP tool '{tool_name}' is BANNED.\n"
            "You must not use black-box tools.\n"
            "ACTION REQUIRED: Write a script in `scratch/` (e.g., `scratch/tmp_tool.py`), "
            "inspect the code, and run it via `Bash`."
        ),
    }
}
print(json.dumps(output))
sys.exit(0)
