#!/usr/bin/env python3
"""
Integration Gate: PreToolUse hook enforcing grep after function edits.

Hook Type: PreToolUse
Latency Target: <10ms

Enforces CLAUDE.md Hard Block #14:
"Integration Blindness (Atomic Bundle): Function edit = Edit + grep.
After ANY function signature change, IMMEDIATELY run grep for that function."

Behavior:
- Checks if there are pending integration greps (set by state_updater after Edit)
- Blocks non-diagnostic tools until grep is run for edited functions
- Allows: Read, Grep, Glob, Bash (for investigation)
- Blocks: Edit, Write, Task (continuation without verification)
"""

import _lib_path  # noqa: F401
import sys
import json

from session_state import (
    load_state, save_state,
    check_integration_blindness,
)


def output_result(decision: str = "approve", reason: str = "", context: str = ""):
    """Output hook result."""
    result = {"hookSpecificOutput": {"hookEventName": "PreToolUse"}}
    if decision == "block":
        result["hookSpecificOutput"]["permissionDecision"] = "deny"
        result["hookSpecificOutput"]["permissionDecisionReason"] = reason
    elif context:
        result["hookSpecificOutput"]["additionalContext"] = context
    print(json.dumps(result))


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        output_result()
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    # Load state
    state = load_state()

    # Auto-expire old pending greps (> 5 turns old)
    current_turn = state.turn_count
    old_count = len(state.pending_integration_greps)
    state.pending_integration_greps = [
        g for g in state.pending_integration_greps
        if current_turn - g.get("turn", 0) <= 5
    ]
    expired = old_count - len(state.pending_integration_greps)

    # Save state if expiries happened
    if expired > 0:
        save_state(state)

    # Check for integration blindness
    # NOTE: Clearing happens in state_updater.py (PostToolUse) to avoid race with other PreToolUse hooks
    should_block, message = check_integration_blindness(state, tool_name, tool_input)

    if should_block:
        output_result(decision="block", reason=message)
    else:
        output_result()

    sys.exit(0)


if __name__ == "__main__":
    main()
