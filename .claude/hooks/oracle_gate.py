#!/usr/bin/env python3
"""
Oracle Gate Hook: Enforce oracle consultation after repeated failures.

Hook Type: PreToolUse (matcher: Edit|Write|Bash)
Behavior: BLOCK after 2 consecutive failures without oracle consultation

THE PROBLEM:
Claude gets stuck in loops, trying the same failing approach. The Three-Strike
Rule (Hard Block #7) says: after 2 failures, run `think` before attempt 3.
This hook enforces that AND suggests oracle for external perspective.

ENFORCEMENT:
1. Track consecutive failures via session_state
2. On failure #2: INJECT strong nudge for oracle
3. On failure #3+: BLOCK until oracle/think is run

Different from existing hooks:
- sunk_cost_detector.py: Detects loops, doesn't block
- thinking_coach.py: Suggests decomposition, doesn't require oracle
"""

import _lib_path  # noqa: F401
import sys
import json

from session_state import load_state, get_turns_since_op

# =============================================================================
# CONFIG
# =============================================================================

# Tools that can break the failure loop
RESET_TOOLS = {"oracle", "think", "council"}

# Turn threshold to consider an oracle "fresh"
ORACLE_FRESHNESS_TURNS = 5


def main():
    """PreToolUse hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Only check action tools (not diagnostic)
    action_tools = {"Edit", "Write", "Bash"}
    if tool_name not in action_tools:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    # Skip diagnostic bash commands
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        diagnostic_patterns = ["ls", "cat", "grep", "find", "echo", "pwd", "which"]
        if any(command.strip().startswith(p) for p in diagnostic_patterns):
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
            sys.exit(0)
        # Skip if running oracle/think/council
        if any(reset in command for reset in RESET_TOOLS):
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
            sys.exit(0)

    # Load state
    state = load_state()
    failures = state.consecutive_failures

    # Check if oracle/think was run recently
    oracle_turns = get_turns_since_op(state, "oracle")
    think_turns = get_turns_since_op(state, "think")
    council_turns = get_turns_since_op(state, "council")
    min_turns = min(oracle_turns, think_turns, council_turns)

    # Reset tracking if oracle was run recently
    if min_turns <= ORACLE_FRESHNESS_TURNS:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    # NUDGE at 2 failures
    if failures == 2:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": (
                    "⚠️ **ORACLE NUDGE** (2 consecutive failures detected)\n\n"
                    "The Three-Strike Rule requires external consultation before attempt #3.\n\n"
                    "**Recommended:**\n"
                    "```bash\n"
                    "python3 .claude/ops/oracle.py --persona skeptic \"Why is this failing?\"\n"
                    "```\n"
                    "OR\n"
                    "```bash\n"
                    "python3 .claude/ops/think.py \"Decompose: <the problem>\"\n"
                    "```\n\n"
                    "Fresh perspective often reveals blind spots."
                ),
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # BLOCK at 3+ failures
    if failures >= 3:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "decision": "block",
                "reason": (
                    f"**ORACLE GATE BLOCKED** (Hard Block #7: Three-Strike Rule)\n\n"
                    f"**{failures} consecutive failures** without oracle/think consultation.\n\n"
                    f"**REQUIRED before continuing:**\n"
                    f"```bash\n"
                    f"python3 .claude/ops/oracle.py --persona skeptic \"Why does X keep failing?\"\n"
                    f"```\n"
                    f"OR\n"
                    f"```bash\n"
                    f"python3 .claude/ops/think.py \"Debug: <summarize the failures>\"\n"
                    f"```\n\n"
                    f"**Why:** Repeated failure = wrong mental model. Get external input.\n"
                    f"**Bypass:** Run oracle/think, or user says \"SUDO CONTINUE\"."
                ),
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # No issues
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
    sys.exit(0)


if __name__ == "__main__":
    main()
