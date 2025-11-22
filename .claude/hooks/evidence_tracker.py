#!/usr/bin/env python3
"""
Evidence Tracker Hook: Tracks tool usage and updates confidence
Triggers on: PostToolUse
"""
import sys
import json
from pathlib import Path

# Add scripts/lib to path
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from lib.epistemology import (
    load_session_state,
    initialize_session_state,
    update_confidence,
    get_confidence_tier,
)

# Load input
try:
    input_data = json.load(sys.stdin)
except:
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

if not tool_name:
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

# Load session state
state = load_session_state(session_id)
if not state:
    state = initialize_session_state(session_id)

# Get current turn
turn = state.get("turn_count", 0)

# Update confidence based on tool usage
old_confidence = state["confidence"]
new_confidence, boost = update_confidence(
    session_id=session_id,
    tool_name=tool_name,
    tool_input=tool_params,
    turn=turn,
    reason=f"{tool_name} usage",
)

# Only show feedback if confidence actually changed
if boost != 0:
    tier_name, _ = get_confidence_tier(new_confidence)

    # Determine what was accessed
    target = ""
    if "file_path" in tool_params:
        target = f" ({Path(tool_params['file_path']).name})"
    elif "query" in tool_params:
        target = f" ('{tool_params['query'][:30]}...')"
    elif "command" in tool_params:
        cmd = tool_params["command"]
        if len(cmd) > 40:
            cmd = cmd[:37] + "..."
        target = f" ({cmd})"

    sign = "+" if boost > 0 else ""
    context = f"""
📈 EVIDENCE GATHERED: {tool_name}{target}
   • Confidence: {old_confidence}% → {new_confidence}% ({sign}{boost}%)
   • Current Tier: {tier_name}
"""

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": context,
                }
            }
        )
    )
else:
    # No confidence change
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
