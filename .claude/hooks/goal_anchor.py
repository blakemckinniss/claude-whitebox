#!/usr/bin/env python3
"""
Goal Anchor Hook: Prevents drift from original user intent.

Hook Type: UserPromptSubmit
Purpose: Captures original goal, surfaces drift warnings.

THE INSIGHT:
Claude often solves the wrong problem. After 5 turns of "fixing" something,
the original ask ("fix the login bug") becomes "refactoring the auth module".
This hook anchors attention to the original goal.

Behavior:
1. On first substantive prompt: Capture goal + keywords
2. On subsequent prompts: Check for drift
3. If drift detected: Inject reminder of original goal
"""

import sys
import json
from pathlib import Path

# Import state machine
from session_state import (
    load_state, save_state, set_goal, check_goal_drift,
    should_nudge, record_nudge,  # v3.4: Nudge tracking
)


def output_hook_result(context: str = ""):
    """Output hook result."""
    result = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit"}}
    if context:
        result["hookSpecificOutput"]["additionalContext"] = context
    print(json.dumps(result))


def main():
    """UserPromptSubmit hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        output_hook_result()
        sys.exit(0)

    prompt = input_data.get("prompt", "")
    if not prompt:
        output_hook_result()
        sys.exit(0)

    # Load state
    state = load_state()

    # Set goal if not already set
    if not state.original_goal:
        set_goal(state, prompt)
        save_state(state)
        output_hook_result()
        sys.exit(0)

    # Check for drift (use prompt as current activity indicator)
    is_drifting, drift_message = check_goal_drift(state, prompt)

    if is_drifting:
        # v3.4: Check nudge history before showing
        show, severity = should_nudge(state, "goal_drift", drift_message)
        if show:
            record_nudge(state, "goal_drift", drift_message)
            # Escalate if repeatedly ignored
            if severity == "escalate":
                drift_message = f"🚨 **REPEATED DRIFT WARNING** (ignored {state.nudge_history.get('goal_drift', {}).get('times_ignored', 0)}x)\n{drift_message}"
            save_state(state)
            output_hook_result(f"\n{drift_message}\n")
            sys.exit(0)

    save_state(state)
    output_hook_result()
    sys.exit(0)


if __name__ == "__main__":
    main()
