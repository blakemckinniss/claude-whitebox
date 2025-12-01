#!/usr/bin/env python3
"""
Deferral Gate Hook: Block deferral theater language.

Hook Type: PreToolUse (matcher: Edit|Write)
Enforces CLAUDE.md Core Principle #19: No Deferral Theater

Detects and blocks:
- "TODO: implement later"
- "# low priority"
- "# nice to have"
- "# could do this later"
- "# worth investigating"
- "# consider adding"

These phrases indicate lazy deferral. Either do it NOW or delete the thought.

Bypass: Include 'SUDO DEFER' in content if deferral is intentional.
"""

import _lib_path  # noqa: F401
import sys
import json
import re

from synapse_core import output_hook_result, check_sudo_in_transcript

# Deferral patterns - phrases that indicate lazy deferral
DEFERRAL_PATTERNS = [
    (r'#\s*(TODO|FIXME):\s*(implement\s+)?later', "TODO later"),
    (r'#\s*low\s+priority', "low priority"),
    (r'#\s*nice\s+to\s+have', "nice to have"),
    (r'#\s*could\s+(do|add|implement)\s+(this\s+)?later', "could do later"),
    (r'#\s*worth\s+investigating', "worth investigating"),
    (r'#\s*consider\s+adding', "consider adding"),
    (r'#\s*future\s+(work|improvement|enhancement)', "future work"),
    (r'#\s*maybe\s+(add|implement)', "maybe add"),
    (r'#\s*might\s+want\s+to', "might want to"),
    (r'#\s*can\s+be\s+(added|done)\s+later', "can be done later"),
]


def check_content_for_deferral(content: str) -> list[str]:
    """Check content for deferral patterns. Returns list of pattern names found."""
    found = []
    for pattern, name in DEFERRAL_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            found.append(name)
    return found


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name not in ("Edit", "Write", "MultiEdit"):
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    transcript_path = data.get("transcript_path", "")

    # Get content to check
    content = ""
    if tool_name == "Write":
        content = tool_input.get("content", "")
    elif tool_name == "Edit":
        content = tool_input.get("new_string", "")
    elif tool_name == "MultiEdit":
        edits = tool_input.get("edits", [])
        content = " ".join(e.get("new_string", "") for e in edits)

    # Bypass check - content or transcript
    if "SUDO DEFER" in content.upper() or check_sudo_in_transcript(transcript_path):
        sys.exit(0)

    # Check for deferral patterns
    deferrals = check_content_for_deferral(content)

    if deferrals:
        names = deferrals[:3]
        output_hook_result(
            "PreToolUse",
            decision="deny",
            reason=(
                f"**DEFERRAL THEATER BLOCKED** (Core Principle #19)\n\n"
                f"Detected: {', '.join(names)}\n\n"
                f"\"Either do it NOW or delete the thought. Future-you doesn't exist.\"\n\n"
                f"Options:\n"
                f"1. Implement the feature now\n"
                f"2. Remove the comment entirely\n"
                f"3. Add 'SUDO DEFER' if deferral is truly intentional"
            )
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
