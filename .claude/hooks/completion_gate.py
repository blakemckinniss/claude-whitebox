#!/usr/bin/env python3
"""
Completion Gate Hook: Block "fixed/done/complete" claims without verification.

Hook Type: PostToolUse (matcher: Edit|Write)
Enforces CLAUDE.md Hard Block #3: "No 'Fixed' claim without verify passing"

After edits that look like bug fixes or feature completions, injects
a reminder that verify must be run before claiming success.

Detection patterns:
- File edits after error discussion
- "fix" in recent file names or content
- Multiple edits to same file (iteration pattern)

This is a PostToolUse hook because we want to remind AFTER the edit,
not block the edit itself.
"""

import _lib_path  # noqa: F401
import sys
import json

from session_state import load_state


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name not in ("Edit", "Write", "MultiEdit"):
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    state = load_state()

    # Check if this looks like a fix iteration
    fix_indicators = []

    # 1. File was edited multiple times (iteration)
    edit_count = sum(1 for f in state.files_edited if f == file_path)
    if edit_count >= 2:
        fix_indicators.append(f"edited {edit_count}x")

    # 2. Recent errors exist
    if state.errors_unresolved:
        fix_indicators.append("unresolved errors exist")

    # 3. "fix" in filename
    if "fix" in file_path.lower():
        fix_indicators.append("'fix' in filename")

    # 4. Check if verify was run recently
    verify_run = getattr(state, 'verify_run', False)

    if fix_indicators and not verify_run:
        # Inject reminder via additionalContext
        output = {
            "hookSpecificOutput": {
                "additionalContext": (
                    f"**VERIFY REMINDER** (Hard Block #3)\n"
                    f"Indicators: {', '.join(fix_indicators)}\n"
                    f"Before claiming 'fixed': run `verify` or tests.\n"
                    f"Pattern: verify command_success \"<test_cmd>\""
                )
            }
        }
        print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()
