#!/usr/bin/env python3
"""
Script Nudge Hook: Suggests writing scripts for complex manual work.

Hook Type: PreToolUse
Latency Target: <5ms

Triggers on:
- Bash commands with 3+ pipes
- Bash commands with loops (for, while, xargs)
- NOT a blocker - just a strong nudge
"""

import sys
import json
import re

# Patterns that suggest "you should script this"
PIPE_THRESHOLD = 3
LOOP_PATTERNS = [
    r'\bfor\s+\w+\s+in\b',      # for x in ...
    r'\bwhile\s+',               # while ...
    r'\bxargs\b',                # xargs (batch processing)
    r'\|\s*while\b',             # | while read
]


def should_nudge(command: str) -> str | None:
    """Return nudge reason if command suggests scripting opportunity."""
    # Count pipes (not inside quotes - rough heuristic)
    pipe_count = command.count('|')
    if pipe_count >= PIPE_THRESHOLD:
        return f"{pipe_count} pipes detected"

    # Check for loop patterns
    for pattern in LOOP_PATTERNS:
        if re.search(pattern, command):
            return "loop/iteration detected"

    return None


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({}))
        sys.exit(0)

    if input_data.get("tool_name") != "Bash":
        print(json.dumps({}))
        sys.exit(0)

    command = input_data.get("tool_input", {}).get("command", "")
    reason = should_nudge(command)

    if reason:
        context = (
            f"⚡ SCRIPT OPPORTUNITY: {reason}\n"
            f"→ Consider: scratch/solve_$(date +%s).py\n"
            f"→ Or proceed if this is genuinely a one-liner"
        )
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": context
            }
        }))
    else:
        print(json.dumps({}))

    sys.exit(0)


if __name__ == "__main__":
    main()
