#!/usr/bin/env python3
"""
Sunk Cost Detector Hook: Breaks "I've invested too much to quit" loops.

Hook Type: PreToolUse
Purpose: Detect when repeated failures signal wrong approach, nudge pivot.

THE INSIGHT:
After 3 failed attempts at the same thing, Claude doubles down rather than
stepping back. This hook asks: "If you were starting fresh, would you still
pick this approach?" - breaking the sunk cost fallacy.

Behavior:
1. Track approach signatures (file + operation pattern)
2. Track consecutive failures (error outputs, failed edits)
3. After 3+ failures or 5+ turns with 2+ failures: Inject pivot nudge
"""

import _lib_path  # noqa: F401
import sys
import json
import re
from pathlib import Path

# Ensure hook directory is in path for local imports
HOOK_DIR = Path(__file__).resolve().parent
if str(HOOK_DIR) not in sys.path:
    sys.path.insert(0, str(HOOK_DIR))

# Import state machine
from session_state import (  # noqa: E402
    load_state, save_state,
    track_approach, check_sunk_cost, get_turns_since_op
)
from synapse_core import log_block, format_block_acknowledgment, get_session_blocks


def output_hook_result(context: str = "", decision: str = "approve", reason: str = "",
                       tool_name: str = "", tool_input: dict = None):
    """Output hook result. Logs blocks for Stop hook reflection."""
    result = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
        }
    }
    if context:
        result["hookSpecificOutput"]["additionalContext"] = context
    if decision == "block":
        result["hookSpecificOutput"]["permissionDecision"] = "deny"
        log_block("sunk_cost_detector", reason, tool_name, tool_input)
        # Add acknowledgment prompt
        result["hookSpecificOutput"]["permissionDecisionReason"] = reason + format_block_acknowledgment("sunk_cost_detector")
    print(json.dumps(result))


def check_repeated_hook_blocks() -> tuple[bool, str]:
    """Check if same hook has blocked 2+ times - suggest fixing the hook.

    Returns: (should_nudge, nudge_message)
    """
    blocks = get_session_blocks()
    if len(blocks) < 2:
        return False, ""

    # Count blocks by hook
    hook_counts = {}
    for block in blocks:
        hook = block.get("hook", "unknown")
        hook_counts[hook] = hook_counts.get(hook, 0) + 1

    # Find hooks that blocked 2+ times
    repeat_offenders = [(h, c) for h, c in hook_counts.items() if c >= 2]
    if not repeat_offenders:
        return False, ""

    # Get the worst offender
    worst_hook, count = max(repeat_offenders, key=lambda x: x[1])

    # Build nudge - suggest fixing the hook directly
    return True, (
        f"🔧 **FIX THE BLOCKER**: `{worst_hook}` has blocked you {count}x.\n"
        f"   This is a hook YOU can edit: `.claude/hooks/{worst_hook}.py`\n"
        f"   → Fix the hook's false positive instead of retrying/asking user.\n"
        f"   → Use Task agent if the hook blocks editing itself."
    )


def extract_approach_signature(tool_name: str, tool_input: dict) -> str:
    """Extract a signature for the current approach.

    Signature = tool + target (file or command pattern)
    """
    if tool_name in ("Edit", "Write", "Read"):
        filepath = tool_input.get("file_path", "")
        if filepath:
            # Use filename + tool as signature
            name = Path(filepath).name if filepath else "unknown"
            return f"{tool_name}:{name}"

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        # Extract key command pattern
        if "pytest" in command:
            return "Bash:pytest"
        if "npm" in command:
            match = re.search(r"npm\s+(\w+)", command)
            if match:
                return f"Bash:npm_{match.group(1)}"
        # Generic: first word
        parts = command.split()
        if parts:
            return f"Bash:{parts[0][:20]}"

    if tool_name == "Task":
        agent_type = tool_input.get("subagent_type", "")
        return f"Task:{agent_type}"

    return f"{tool_name}:generic"


def main():
    """PreToolUse hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        output_hook_result()
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Skip low-signal tools
    skip_tools = {"TodoWrite", "BashOutput", "KillShell", "Glob", "Grep"}
    if tool_name in skip_tools:
        output_hook_result()
        sys.exit(0)

    # Load state
    state = load_state()

    # Track approach
    signature = extract_approach_signature(tool_name, tool_input)
    track_approach(state, signature)

    # Check sunk cost trap
    is_trapped, nudge_message = check_sunk_cost(state)

    # Check for repeated hook blocks - nudge to fix the hook
    has_repeat_blocks, block_nudge = check_repeated_hook_blocks()

    # THREE-STRIKE RULE (Hard Block #7):
    # After 3+ failures, BLOCK until /think runs
    turns_since_think = get_turns_since_op(state, "think")
    should_block = (
        state.consecutive_failures >= 3
        and turns_since_think > 3  # Must have run /think in last 3 turns
    )

    save_state(state)

    if should_block:
        output_hook_result(
            decision="block",
            reason=(
                f"**THREE-STRIKE BLOCKED** (Hard Block #7)\n"
                f"Consecutive failures: {state.consecutive_failures}\n"
                f"Run `/think \"<problem>\"` before 3rd attempt.\n"
                f"Last /think: {turns_since_think} turns ago"
            ),
            tool_name=tool_name,
            tool_input=tool_input
        )
    elif has_repeat_blocks:
        # Prioritize "fix the hook" nudge over general sunk cost
        output_hook_result(f"\n{block_nudge}\n")
    elif is_trapped:
        output_hook_result(f"\n{nudge_message}\n")
    else:
        output_hook_result()

    sys.exit(0)


if __name__ == "__main__":
    main()
