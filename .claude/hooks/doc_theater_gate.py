#!/usr/bin/env python3
"""
Documentation Theater Gate: Blocks creation of standalone documentation files.

Hook Type: PreToolUse
Latency Target: <50ms

Blocks Write tool when targeting common documentation patterns:
- README.md, SCHEMAS.md, GUIDE.md, etc.
- Any .md file in non-standard locations

Allows:
- CLAUDE.md (the constitution)
- .claude/commands/*.md (slash commands)
- .claude/memory/*.md (persistent memory)
- Code files with inline docstrings (the right way)

Philosophy: Standalone docs rot; inline docs get read.
"""

import sys
import json
import re
from pathlib import Path

# Patterns that indicate documentation theater
DOC_THEATER_PATTERNS = [
    r'README\.md$',
    r'GUIDE\.md$',
    r'SCHEMA[S]?\.md$',
    r'REFERENCE\.md$',
    r'DOCS?\.md$',
    r'CONTRIBUTING\.md$',
    r'CHANGELOG\.md$',
    r'ARCHITECTURE\.md$',
    r'DESIGN\.md$',
    r'API\.md$',
    r'USAGE\.md$',
    r'SETUP\.md$',
    r'INSTALL\.md$',
    r'OVERVIEW\.md$',
]

# Allowed markdown locations
ALLOWED_MD_PATHS = [
    r'/CLAUDE\.md$',                    # Constitution
    r'\.claude/commands/.*\.md$',       # Slash commands
    r'\.claude/memory/.*\.md$',         # Persistent memory
    r'\.claude/agents/.*\.md$',         # Subagent definitions
    r'\.claude/skills/.*\.md$',         # Skill definitions
    r'projects/.*/.*\.md$',             # Project-specific docs (user owns these)
]


def is_doc_theater(file_path: str) -> tuple[bool, str]:
    """Check if file path looks like documentation theater."""

    # Check if it's an allowed location first
    for pattern in ALLOWED_MD_PATHS:
        if re.search(pattern, file_path):
            return False, ""

    # Check for obvious doc theater patterns
    for pattern in DOC_THEATER_PATTERNS:
        if re.search(pattern, file_path, re.IGNORECASE):
            return True, f"Matches doc theater pattern: {pattern}"

    # Any other .md file outside allowed locations is suspicious
    if file_path.endswith('.md'):
        return True, "Standalone .md file outside allowed locations"

    return False, ""


def main():
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({}))
        sys.exit(0)

    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})

    # Only check Write tool
    if tool_name != "Write":
        print(json.dumps({}))
        sys.exit(0)

    file_path = tool_input.get("file_path", "")

    is_theater, reason = is_doc_theater(file_path)

    if is_theater:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"🎭 DOCUMENTATION THEATER BLOCKED\n"
                    f"File: {Path(file_path).name}\n"
                    f"Reason: {reason}\n\n"
                    f"Principle 19: Never create standalone docs you wouldn't read.\n"
                    f"Put documentation INLINE (docstrings, comments at point-of-use).\n\n"
                    f"Allowed .md locations:\n"
                    f"  • CLAUDE.md (constitution)\n"
                    f"  • .claude/commands/*.md (slash commands)\n"
                    f"  • .claude/memory/*.md (persistent memory)\n"
                    f"  • projects/*/*.md (user-owned)\n\n"
                    f"User can override with SUDO if truly needed."
                )
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    print(json.dumps({}))
    sys.exit(0)


if __name__ == "__main__":
    main()
