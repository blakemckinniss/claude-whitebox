#!/usr/bin/env python3
"""
Command Tracker Hook: Tracks workflow command execution
Triggers on: PostToolUse
Purpose: Record when /verify, /upkeep, /xray, /think, /audit, /void, /research are run
"""
import sys
import json
import re
from pathlib import Path

# Add scripts/lib to path
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.epistemology import record_command_run, load_session_state

# Load input
try:
    input_data = json.load(sys.stdin)
except Exception:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "",
                }
            }
        )
    )
    sys.exit(0)

session_id = input_data.get("sessionId", "unknown")
tool_name = input_data.get("toolName", "")
tool_params = input_data.get("toolParams", {})

# Only track Bash commands (where workflow commands are executed)
if tool_name != "Bash":
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "",
                }
            }
        )
    )
    sys.exit(0)

command = tool_params.get("command", "")
if not command:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "",
                }
            }
        )
    )
    sys.exit(0)

# Load state to get turn count
state = load_session_state(session_id)
turn = state.get("turn_count", 0) if state else 0

# Detect workflow commands
# Match both: scripts/ops/verify.py and /verify (slash command alias)
command_patterns = {
    "verify": r"(scripts/ops/verify\.py|/verify\s)",
    "upkeep": r"(scripts/ops/upkeep\.py|/upkeep)",
    "xray": r"(scripts/ops/xray\.py|/xray\s)",
    "think": r"(scripts/ops/think\.py|/think\s)",
    "audit": r"(scripts/ops/audit\.py|/audit\s)",
    "void": r"(scripts/ops/void\.py|/void\s)",
    "research": r"(scripts/ops/research\.py|/research\s)",
}

for cmd_name, pattern in command_patterns.items():
    if re.search(pattern, command):
        record_command_run(session_id, cmd_name, turn, command)
        break  # Only record once per command

# Silent tracking (no context injection - just state updates)
print(
    json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "",
            }
        }
    )
)
sys.exit(0)
