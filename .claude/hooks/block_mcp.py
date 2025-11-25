#!/usr/bin/env python3
"""Block MCP tools - forces whitebox approach"""
import sys
import json

def check_sudo_in_transcript(data: dict) -> bool:
    """Check if SUDO keyword is in recent transcript messages."""
    transcript_path = data.get("transcript_path", "")
    if not transcript_path:
        return False
    try:
        import os
        if os.path.exists(transcript_path):
            with open(transcript_path, 'r') as tf:
                transcript = tf.read()
                # Check last 5000 chars for SUDO (recent messages)
                last_chunk = transcript[-5000:] if len(transcript) > 5000 else transcript
                return "SUDO" in last_chunk
    except Exception:
        pass
    return False



try:
    input_data = json.load(sys.stdin)

    # SUDO escape hatch
    if check_sudo_in_transcript(input_data):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "additionalContext": "⚠️ SUDO bypass - hook check skipped"
            }
        }))
        sys.exit(0)
except (json.JSONDecodeError, ValueError):
    sys.exit(0)

tool_name = input_data.get("tool_name", "Unknown")

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
