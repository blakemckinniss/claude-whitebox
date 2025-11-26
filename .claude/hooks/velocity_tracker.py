#!/usr/bin/env python3
"""
Velocity Tracker Hook: Detect spinning vs actual progress.

Hook Type: PostToolUse
Purpose: Detect oscillation patterns (edit→read→edit→read) without explicit errors.

THE INSIGHT:
Sunk cost detector catches failures. But Claude can also "spin" without failing:
- Reading the same file repeatedly
- Editing, then re-reading to check, then editing again
- Pattern: high tool activity, low net progress

This hook measures "velocity" = net progress / tool calls.

Signals:
1. Same file read 3+ times in 5 turns → "re-reading loop"
2. File edited then read within 2 turns → "checking own work loop"
3. Tool diversity < 2 unique tools in 5 turns → "monotonic activity"

Output: Warning message to inject self-reflection before continuing.
"""

import sys
import json
from collections import Counter
from session_state import load_state

# =============================================================================
# PATTERNS
# =============================================================================

def detect_oscillation(state) -> tuple[bool, str]:
    """Detect oscillation patterns in recent tool usage.

    Returns: (is_oscillating, message)
    """
    last_5 = state.last_5_tools
    if len(last_5) < 4:
        return False, ""

    # Pattern 1: Same tool 4+ times (already caught by scratch_enforcer)
    # Skip - handled elsewhere

    # Pattern 2: Read→Edit→Read→Edit oscillation
    read_edit_pattern = []
    for tool in last_5:
        if tool in ("Read", "Edit", "Write"):
            read_edit_pattern.append("R" if tool == "Read" else "E")

    pattern_str = "".join(read_edit_pattern)
    if "RERE" in pattern_str or "ERER" in pattern_str:
        return True, "🔄 OSCILLATION: Read→Edit→Read→Edit pattern detected.\n💡 Step back: Are you making progress or checking the same thing repeatedly?"

    # Pattern 3: Low tool diversity with high activity
    if len(last_5) == 5:
        unique_tools = len(set(last_5))
        if unique_tools <= 2 and all(t in ("Read", "Glob", "Grep") for t in last_5):
            return True, "🔄 SEARCH LOOP: 5+ searches without action.\n💡 Do you have enough info to act, or are you avoiding a decision?"

    return False, ""


def detect_rereading(state) -> tuple[bool, str]:
    """Detect same file being read multiple times.

    Returns: (is_rereading, message)
    """
    # Check files_read for duplicates (recent 10)
    recent_reads = state.files_read[-10:] if len(state.files_read) >= 10 else state.files_read

    read_counts = Counter(recent_reads)
    repeated = [(f, c) for f, c in read_counts.items() if c >= 3]

    if repeated:
        file, count = repeated[0]
        # Extract just filename
        name = file.split("/")[-1] if "/" in file else file
        return True, f"🔄 RE-READ: `{name}` read {count}x recently.\n💡 What are you looking for that you haven't found?"

    return False, ""


def detect_check_own_work(state) -> tuple[bool, str]:
    """Detect editing then immediately reading same file.

    Returns: (is_checking, message)
    """
    if len(state.last_5_tools) < 3:
        return False, ""

    # Find Edit/Write followed by Read
    files_edited_recently = set(state.files_edited[-3:]) if state.files_edited else set()
    files_read_recently = set(state.files_read[-3:]) if state.files_read else set()

    overlap = files_edited_recently & files_read_recently

    if overlap and state.last_5_tools[-1] == "Read" and state.last_5_tools[-2] in ("Edit", "Write"):
        name = list(overlap)[0].split("/")[-1]
        return True, f"🔄 SELF-CHECK: Edited then re-read `{name}`.\n💡 Trust your edit or verify with a test, not re-reading."

    return False, ""


# =============================================================================
# MAIN
# =============================================================================

def main():
    """PostToolUse hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({}))
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")

    # Only analyze after meaningful tools
    if tool_name not in ("Read", "Edit", "Write", "Bash", "Glob", "Grep"):
        print(json.dumps({}))
        sys.exit(0)

    # Load state
    state = load_state()

    # Check patterns (first match wins)
    checks = [
        detect_oscillation,
        detect_rereading,
        detect_check_own_work,
    ]

    context = ""
    for check in checks:
        is_detected, message = check(state)
        if is_detected:
            context = f"\n{message}\n"
            break

    # Output
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": context
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
