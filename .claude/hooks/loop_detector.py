#!/usr/bin/env python3
"""
Loop Detector: PreToolUse hook blocking bash loops.

Hook Type: PreToolUse (matcher: Bash)
Latency Target: <5ms

Enforces CLAUDE.md Hard Block #6:
"Bash loops on files are BANNED. Use parallel.py or swarm."
"""

import _lib_path  # noqa: F401
import sys
import json
import re

from synapse_core import check_sudo_in_transcript, log_block, format_block_acknowledgment

# Patterns that indicate bash loops
LOOP_PATTERNS = [
    r'\bfor\s+\w+\s+in\b',           # for x in ...
    r'\bwhile\s+',                    # while ...
    r'\buntil\s+',                    # until ...
    r'\|\s*while\b',                  # | while read
    r'\bxargs\s+.*\bsh\b',           # xargs sh -c (loop equivalent)
    r'\bfind\s+.*-exec\b',           # find -exec (loop equivalent)
]

# Allowed loop-like patterns (false positives)
ALLOWED_PATTERNS = [
    r'for\s+\w+\s+in\s+\$\(',        # for x in $(command) - one-liner OK
    r'while\s+read.*<<<',             # while read <<< - single input OK
    r'python[3]?\s+.*-c\s+["\']',    # python -c "..." - Python code, not bash loops
]


def output_result(decision: str = "approve", reason: str = "", context: str = "",
                  tool_name: str = "", tool_input: dict = None):
    """Output hook result. Logs blocks for Stop hook reflection."""
    result = {"hookSpecificOutput": {"hookEventName": "PreToolUse"}}
    if decision == "block":
        result["hookSpecificOutput"]["permissionDecision"] = "deny"
        log_block("loop_detector", reason, tool_name, tool_input)
        # Add acknowledgment prompt
        result["hookSpecificOutput"]["permissionDecisionReason"] = reason + format_block_acknowledgment("loop_detector")
    elif context:
        result["hookSpecificOutput"]["additionalContext"] = context
    print(json.dumps(result))


def is_bash_loop(command: str) -> tuple[bool, str]:
    """Check if command contains banned loop constructs."""
    # Check allowed patterns first (false positive prevention)
    for pattern in ALLOWED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return False, ""

    # Check for banned loops
    for pattern in LOOP_PATTERNS:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            return True, match.group(0)

    return False, ""


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        output_result()
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name != "Bash":
        output_result()
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    transcript_path = data.get("transcript_path", "")
    command = tool_input.get("command", "")

    # Check for SUDO bypass in transcript
    if check_sudo_in_transcript(transcript_path):
        output_result()
        sys.exit(0)

    if not command:
        output_result()
        sys.exit(0)

    is_loop, matched = is_bash_loop(command)

    if is_loop:
        output_result(
            decision="block",
            reason=f"**BASH LOOP BLOCKED** (Hard Block #6)\n"
                   f"Detected: `{matched}`\n"
                   f"Use `parallel.py` or `swarm` instead of bash loops.\n"
                   f"Bypass: Include 'SUDO LOOP' in command description.",
            tool_name=tool_name,
            tool_input=tool_input
        )
        sys.exit(0)

    output_result()
    sys.exit(0)


if __name__ == "__main__":
    main()
