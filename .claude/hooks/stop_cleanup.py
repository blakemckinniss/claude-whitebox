#!/usr/bin/env python3
"""
Stop Cleanup Hook: Fires on Ctrl+C interrupt.

Hook Type: Stop
Latency Target: <100ms

Warns about:
- Files created with stubs/TODOs (abandoned work)
- Pending integration greps (incomplete verification)
- Unresolved errors

This is the last chance to remind about incomplete work before session ends.

VALID OUTPUT SCHEMA (Stop hooks):
{
    "continue": bool,        # optional
    "suppressOutput": bool,  # optional
    "stopReason": string     # optional - use this for messages
}

NOTE: Stop hooks do NOT support hookSpecificOutput - only PreToolUse,
UserPromptSubmit, and PostToolUse have hookSpecificOutput schemas.
"""

import _lib_path  # noqa: F401
import sys
import json
from pathlib import Path

from session_state import load_state

# Stub patterns to detect
STUB_PATTERNS = [
    b'TODO',
    b'FIXME',
    b'NotImplementedError',
    b'raise NotImplementedError',
    b'pass  #',
    b'...  #',
]

CODE_EXTENSIONS = {'.py', '.js', '.ts', '.tsx', '.rs', '.go', '.java'}


def check_stubs_in_created_files(state) -> list[str]:
    """Check created files for stubs."""
    warnings = []

    for filepath in state.files_created[-10:]:  # Last 10 created
        path = Path(filepath)
        if not path.exists() or path.suffix not in CODE_EXTENSIONS:
            continue

        try:
            content = path.read_bytes()
            stubs = [p.decode() for p in STUB_PATTERNS if p in content]
            if stubs:
                warnings.append(f"  • `{path.name}`: {', '.join(stubs[:2])}")
        except (OSError, PermissionError):
            pass

    return warnings


def main():
    try:
        json.load(sys.stdin)  # Consume input
    except (json.JSONDecodeError, ValueError):
        pass

    state = load_state()
    messages = []

    # Check for abandoned stubs
    stub_warnings = check_stubs_in_created_files(state)
    if stub_warnings:
        messages.append("⚠️ **ABANDONED WORK** - Files with stubs:")
        messages.extend(stub_warnings)

    # Check for pending integration greps
    pending = state.pending_integration_greps
    if pending:
        funcs = [p.get("function", "unknown") for p in pending[:3]]
        messages.append(f"⚠️ **UNVERIFIED EDITS** - Functions need grep: {', '.join(funcs)}")

    # Check for unresolved errors
    if state.errors_unresolved:
        error = state.errors_unresolved[-1]
        messages.append(f"⚠️ **UNRESOLVED ERROR**: {error.get('type', 'unknown')[:50]}")

    # Output - Stop hooks don't support hookSpecificOutput, use stopReason
    if messages:
        output = {
            "stopReason": "\n".join(messages)
        }
        print(json.dumps(output))
    # No output needed if nothing to report

    sys.exit(0)


if __name__ == "__main__":
    main()
