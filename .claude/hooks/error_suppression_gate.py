#!/usr/bin/env python3
"""
Error Suppression Gate: PreToolUse hook blocking work until errors are resolved.

Hook Type: PreToolUse
Latency Target: <10ms

Enforces CLAUDE.md Hard Block #18:
"If a tool execution returns stderr or exit code > 0, you are FORBIDDEN from
ignoring it or attempting a 'workaround' implementation. You MUST diagnose
and resolve the error before returning to the main task."

Behavior:
- Tracks unresolved errors from session_state
- Blocks non-diagnostic tool calls until error is addressed
- Allows: Bash, Read, Grep, Glob (diagnostic tools)
- Blocks: Edit, Write, Task, etc. (continuation tools)
"""

import _lib_path  # noqa: F401
import sys
import json
import time

from session_state import load_state


# Tools allowed even with unresolved errors (for debugging)
DIAGNOSTIC_TOOLS = frozenset({
    "Read", "Grep", "Glob", "Bash", "BashOutput",
    "WebFetch", "WebSearch", "AskUserQuestion",
    "TodoWrite", "KillShell"
})

# Errors that auto-expire (not blocking after N seconds)
ERROR_TTL_SECONDS = 300  # 5 minutes


def output_result(decision: str = "approve", reason: str = "", context: str = ""):
    """Output hook result."""
    result = {"hookSpecificOutput": {"hookEventName": "PreToolUse"}}
    if decision == "block":
        result["decision"] = "block"
        result["reason"] = reason
    elif context:
        result["hookSpecificOutput"]["additionalContext"] = context
    print(json.dumps(result))


def get_recent_unresolved_errors(state) -> list:
    """Get unresolved errors within TTL."""
    cutoff = time.time() - ERROR_TTL_SECONDS
    return [
        e for e in state.errors_unresolved
        if e.get("timestamp", 0) > cutoff
    ]


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        output_result()
        sys.exit(0)

    tool_name = data.get("tool_name", "")

    # Always allow diagnostic tools
    if tool_name in DIAGNOSTIC_TOOLS:
        output_result()
        sys.exit(0)

    # Load state
    state = load_state()

    # Check for recent unresolved errors
    recent_errors = get_recent_unresolved_errors(state)

    if not recent_errors:
        output_result()
        sys.exit(0)

    # Get most recent error
    latest = recent_errors[-1]
    error_type = latest.get("type", "Unknown error")[:60]
    error_details = latest.get("details", "")[:100]
    age_seconds = int(time.time() - latest.get("timestamp", 0))

    # BLOCK non-diagnostic tools
    output_result(
        decision="block",
        reason=(
            f"**ERROR SUPPRESSION BLOCKED** (Hard Block #18)\n"
            f"Unresolved: {error_type}\n"
            f"Details: {error_details}...\n"
            f"Age: {age_seconds}s\n\n"
            f"REQUIRED: Fix the error before continuing.\n"
            f"Allowed tools: Bash, Read, Grep, Glob (for debugging)\n"
            f"Bypass: Resolve the error or wait {ERROR_TTL_SECONDS - age_seconds}s for expiry."
        )
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
