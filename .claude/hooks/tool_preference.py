#!/usr/bin/env python3
"""
Tool Preference Hook: PreToolUse intercept for better tool choices.

Hook Type: PreToolUse
Latency Target: <10ms

Problem: Claude defaults to WebFetch/WebSearch when firecrawl/research are better
Solution: Intercept and suggest alternatives with clear reasoning
"""

import sys
import json
import re

# =============================================================================
# TOOL REDIRECTS
# =============================================================================

TOOL_PREFERENCES = {
    "WebFetch": {
        "better_tool": "firecrawl.py",
        "reason": "Firecrawl extracts cleaner markdown, handles JS-rendered content",
        "command": "python3 scripts/ops/firecrawl.py scrape <URL>",
        "exceptions": ["github.com/raw", "api.", "json"],  # Allow direct API calls
    },
    "WebSearch": {
        "better_tool": "research.py",
        "reason": "Tavily provides summarized, relevant results with less noise",
        "command": "python3 scripts/ops/research.py \"<query>\"",
        "exceptions": [],
    },
}


def check_exceptions(tool_name: str, tool_input: dict) -> bool:
    """Check if this specific call should bypass the preference."""
    prefs = TOOL_PREFERENCES.get(tool_name, {})
    exceptions = prefs.get("exceptions", [])

    # Check URL for WebFetch
    if tool_name == "WebFetch":
        url = tool_input.get("url", "")
        for exc in exceptions:
            if exc in url.lower():
                return True

    return False


def main():
    """PreToolUse hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Check if this tool has a preferred alternative
    if tool_name not in TOOL_PREFERENCES:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    # Check for exceptions
    if check_exceptions(tool_name, tool_input):
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse"}}))
        sys.exit(0)

    prefs = TOOL_PREFERENCES[tool_name]

    # Build suggestion message
    message = (
        f"⚡ TOOL PREFERENCE: Consider `{prefs['better_tool']}` instead of {tool_name}\n"
        f"   Why: {prefs['reason']}\n"
        f"   Run: {prefs['command']}"
    )

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": message,
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
