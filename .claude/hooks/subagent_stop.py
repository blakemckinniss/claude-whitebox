#!/usr/bin/env python3
"""
SubagentStop Hook: Fires when Task tool agents finish.

Hook Type: SubagentStop
Latency Target: <100ms

Same quality checks as Stop hook - ensures subagents don't leave
abandoned work or unverified edits. Also checks for session blocks.

Input: session_id, transcript_path, permission_mode, hook_event_name, stop_hook_active
Output: { "decision": "block", "reason": string } or nothing
"""

import _lib_path  # noqa: F401
import sys
import json
from pathlib import Path

from session_state import load_state
from synapse_core import get_session_blocks, clear_session_blocks

STUB_PATTERNS = [
    b'TODO',
    b'FIXME',
    b'NotImplementedError',
    b'pass  #',
]

CODE_EXTENSIONS = {'.py', '.js', '.ts', '.tsx', '.rs', '.go', '.java'}


def check_stubs_in_created_files(state) -> list[str]:
    """Check created files for stubs."""
    warnings = []

    for filepath in state.files_created[-5:]:  # Last 5 for subagents
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
        json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        pass

    state = load_state()
    messages = []
    must_reflect = False

    # Check for session blocks (subagent may have triggered some)
    blocks = get_session_blocks()
    if blocks:
        must_reflect = True
        hook_counts = {}
        for b in blocks:
            hook = b.get("hook", "unknown")
            hook_counts[hook] = hook_counts.get(hook, 0) + 1
        messages.append("🚨 Subagent hit blocks:")
        for hook, count in sorted(hook_counts.items(), key=lambda x: -x[1])[:3]:
            messages.append(f"  • `{hook}`: {count}x")

        # Clear blocks after showing - prevents repeated reflection demands
        clear_session_blocks()

    # Check for abandoned stubs
    stub_warnings = check_stubs_in_created_files(state)
    if stub_warnings:
        messages.append("⚠️ Subagent left stubs:")
        messages.extend(stub_warnings)

    # Check for pending integration greps
    pending = state.pending_integration_greps
    if pending:
        funcs = [p.get("function", "?") for p in pending[:2]]
        messages.append(f"⚠️ Unverified edits: {', '.join(funcs)}")

    if must_reflect:
        output = {"decision": "block", "reason": "\n".join(messages)}
        print(json.dumps(output))
    elif messages:
        output = {"stopReason": "\n".join(messages)}
        print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()
