#!/usr/bin/env python3
"""
Scratch Enforcer Gate Hook (PreToolUse)

HARD BLOCKS tool usage when in ENFORCE phase.
Only triggers if pattern threshold exceeded AND phase == "enforce".

BYPASS MECHANISM:
- User includes "MANUAL" keyword → Allow + track as potential false positive
- User includes "SUDO MANUAL" → Allow + no penalty
"""

import sys
import json
from pathlib import Path

# Add scripts/lib to path
PROJECT_DIR = Path.cwd()
while not (PROJECT_DIR / "scripts" / "lib").exists() and PROJECT_DIR != PROJECT_DIR.parent:
    PROJECT_DIR = PROJECT_DIR.parent

sys.path.insert(0, str(PROJECT_DIR / "scripts" / "lib"))

from scratch_enforcement import (
    get_enforcement_state,
    detect_pattern_in_history,
    should_enforce,
    update_pattern_detection,
    log_telemetry,
    PATTERNS,
)


def main():
    """Main hook logic"""
    try:
        data = json.load(sys.stdin)
    except:
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    turn = data.get("turn", 0)
    prompt = data.get("prompt", "")

    # Only track file operation tools
    if tool_name not in ["Read", "Grep", "Glob", "Edit"]:
        sys.exit(0)

    # Load state
    state = get_enforcement_state()

    # Only enforce in ENFORCE phase
    if state["phase"] != "enforce":
        sys.exit(0)

    # Build tool history from telemetry (simplified for now)
    tool_history = [{"tool": tool_name, "turn": turn}]

    # Detect pattern
    detection = detect_pattern_in_history(tool_name, tool_history, turn)

    if detection:
        pattern_name, count = detection

        # Check if should enforce (includes bypass check)
        action, message = should_enforce(pattern_name, state, prompt)

        if action == "block" and message:
            # HARD BLOCK
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": message
                }
            }
            print(json.dumps(output))
            log_telemetry(turn, pattern_name, "hard_blocked", [tool_name])
            sys.exit(0)

        elif action == "observe":
            # Bypass triggered - track as potential false positive
            if "MANUAL" in prompt:
                update_pattern_detection(pattern_name, 0, script_written=False, bypassed=True)
                log_telemetry(turn, pattern_name, "bypassed_manual", [tool_name])

    # Allow execution (default)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow"
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
