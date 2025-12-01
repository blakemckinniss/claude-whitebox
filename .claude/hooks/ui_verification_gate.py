#!/usr/bin/env python3
"""
UI Verification Gate Hook: Require browser screenshot after CSS/UI changes.

Hook Type: PostToolUse (matcher: Edit|Write)
Enforces CLAUDE.md Auto-Invoke Rule: "Claiming UI/CSS change works -> browser page screenshot"

After editing CSS, style, or UI files, injects reminder to verify with browser.

Detection:
- .css, .scss, .less files
- style/styles in filename
- CSS-in-JS patterns (styled, className, sx prop)
- Tailwind classes

This is PostToolUse because we remind AFTER the edit, not block it.
"""

import _lib_path  # noqa: F401
import sys
import json
import re

from session_state import load_state

# File patterns that indicate UI/CSS work
UI_FILE_PATTERNS = [
    r'\.css$',
    r'\.scss$',
    r'\.less$',
    r'\.sass$',
    r'style',
    r'theme',
    r'\.tsx$',  # React components often have styles
    r'\.vue$',
    r'\.svelte$',
]

# Content patterns that indicate style changes
STYLE_CONTENT_PATTERNS = [
    r'className\s*=',
    r'style\s*=\s*\{',
    r'styled\.',
    r'css`',
    r'@apply\s+',  # Tailwind
    r'sx\s*=\s*\{',  # MUI
    r'class\s*=\s*["\'][\w\s-]+["\']',  # HTML classes
    r'(background|color|margin|padding|display|flex|grid|width|height)\s*:',
]


def is_ui_change(file_path: str, content: str) -> list[str]:
    """Check if this looks like a UI/CSS change. Returns list of indicators."""
    indicators = []

    # Check file path
    for pattern in UI_FILE_PATTERNS:
        if re.search(pattern, file_path, re.IGNORECASE):
            indicators.append(f"UI file: {pattern}")
            break

    # Check content for style patterns
    for pattern in STYLE_CONTENT_PATTERNS:
        if re.search(pattern, content):
            indicators.append(f"style pattern detected")
            break

    return indicators


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

    # Get content
    content = ""
    if tool_name == "Write":
        content = tool_input.get("content", "")
    elif tool_name == "Edit":
        content = tool_input.get("new_string", "")

    indicators = is_ui_change(file_path, content)
    if not indicators:
        sys.exit(0)

    # Check if browser screenshot was taken recently
    state = load_state()
    browser_used = getattr(state, 'browser_screenshot_taken', False)

    if browser_used:
        sys.exit(0)

    # Inject reminder
    output = {
        "hookSpecificOutput": {
            "additionalContext": (
                f"**UI VERIFICATION NEEDED** (Auto-Invoke Rule)\n"
                f"Detected: {', '.join(indicators[:2])}\n"
                f"Before claiming UI works, run:\n"
                f"```bash\n"
                f"browser page screenshot -o .claude/tmp/ui_check.png\n"
                f"```"
            )
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
