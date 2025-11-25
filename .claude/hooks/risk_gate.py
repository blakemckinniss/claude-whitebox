#!/usr/bin/env python3
"""
Risk Gate Hook: Detects dangerous commands and increments risk
Triggers on: PreToolUse (Bash commands)
"""
import sys
import json
import os
from pathlib import Path


def check_sudo_in_transcript(data: dict) -> bool:
    """Check if SUDO keyword is in recent transcript messages."""
    transcript_path = data.get("transcript_path", "")
    if not transcript_path:
        return False
    try:
        if os.path.exists(transcript_path):
            with open(transcript_path, 'r') as tf:
                transcript = tf.read()
                last_chunk = transcript[-5000:] if len(transcript) > 5000 else transcript
                return "SUDO" in last_chunk
    except Exception:
        pass
    return False

# Add scripts/lib to path
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.epistemology import (
    load_session_state,
    initialize_session_state,
    increment_risk,
    get_risk_level,
    is_dangerous_command,
    check_risk_threshold,
)

# Load input
try:
    input_data = json.load(sys.stdin)
except Exception as e:
    # SECURITY: Fail CLOSED on error (deny, not allow)
    error_msg = f"Risk gate failed to parse input: {type(e).__name__}"
    print(error_msg, file=sys.stderr)
    # Still allow on JSON parse error (not a security risk, just malformed hook input)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow"
        }
    }))
    sys.exit(0)

# SUDO escape hatch
if check_sudo_in_transcript(input_data):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "additionalContext": "⚠️ SUDO bypass - risk gate check skipped"
        }
    }))
    sys.exit(0)

session_id = input_data.get("session_id", "unknown")
tool_name = input_data.get("tool_name", "")
tool_params = input_data.get("tool_input", {})

# Only check Bash commands for dangerous patterns
if tool_name != "Bash":
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow"
        }
    }))
    sys.exit(0)

command = tool_params.get("command", "")
if not command:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow"
        }
    }))
    sys.exit(0)

# Check if command is dangerous
danger_result = is_dangerous_command(command)

if danger_result:
    pattern, reason = danger_result

    # Load session state
    state = load_session_state(session_id)
    if not state:
        state = initialize_session_state(session_id)

    turn = state.get("turn_count", 0)

    # Increment risk by 20%
    new_risk = increment_risk(
        session_id=session_id,
        amount=20,
        turn=turn,
        reason=f"Dangerous command blocked: {reason}",
        command=command,
    )

    risk_level, risk_desc = get_risk_level(new_risk)

    # Check if we need council trigger
    council_msg = check_risk_threshold(session_id)

    # Build block message
    block_message = f"""🚫 DANGEROUS COMMAND BLOCKED

Command: {command[:100]}
Pattern: {pattern}
Reason: {reason}

Risk Increased: +20%
New Risk Level: {new_risk}% ({risk_level})
{risk_desc}
"""

    if council_msg:
        block_message += f"\n{council_msg}"

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": block_message
        }
    }))
    sys.exit(0)

# Safe command
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow"
    }
}))
sys.exit(0)
