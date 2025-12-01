#!/usr/bin/env python3
"""
Commit Gate Hook: Block git commit without running upkeep first.

Hook Type: PreToolUse (matcher: Bash)
Enforces CLAUDE.md Hard Block #4: "No Commit without running upkeep first"

Detects:
- git commit (any form)
- git push (warn if no recent commit verification)

Bypass: Include 'SUDO COMMIT' in command or description.
"""

import _lib_path  # noqa: F401
import sys
import json
import re

from session_state import load_state
from synapse_core import output_hook_result, check_sudo_in_transcript


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name != "Bash":
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    transcript_path = data.get("transcript_path", "")
    command = tool_input.get("command", "")
    description = tool_input.get("description", "")

    # Bypass check - command/description or transcript
    combined = f"{command} {description}".upper()
    if "SUDO COMMIT" in combined or check_sudo_in_transcript(transcript_path):
        sys.exit(0)

    # Detect git commit
    commit_patterns = [
        r'\bgit\s+commit\b',
        r'\bgit\s+.*\bcommit\b',
    ]

    is_commit = any(re.search(p, command, re.IGNORECASE) for p in commit_patterns)
    if not is_commit:
        sys.exit(0)

    # Check if upkeep was run this session
    state = load_state()

    # Check session state for upkeep run
    upkeep_run = getattr(state, 'upkeep_run', False)

    # Also check commands_run for upkeep invocation
    commands = getattr(state, 'commands_run', [])
    upkeep_in_commands = any('upkeep' in str(cmd).lower() for cmd in commands[-20:])

    if upkeep_run or upkeep_in_commands:
        sys.exit(0)

    # BLOCK - no upkeep detected
    output_hook_result(
        "PreToolUse",
        decision="deny",
        reason=(
            "**COMMIT BLOCKED** (Hard Block #4)\n\n"
            "MUST run `upkeep` before committing.\n\n"
            "```bash\n"
            ".claude/.venv/bin/python .claude/ops/upkeep.py\n"
            "```\n\n"
            "Bypass: Add 'SUDO COMMIT' to description if upkeep already ran."
        )
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
