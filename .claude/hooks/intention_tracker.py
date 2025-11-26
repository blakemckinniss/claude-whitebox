#!/usr/bin/env python3
"""
Intention Tracker Hook v3.2: UserPromptSubmit hook for pending file/search extraction.

Hook Type: UserPromptSubmit
Latency Target: <20ms

THE CORE INSIGHT:
Claude often announces intentions ("I'll check X, Y, Z") but then only acts on X.
This hook extracts mentioned files/searches and tracks them as "pending".
Later hooks (batch_intercept) can warn if pending items aren't being batched.

Patterns detected:
- File paths: config.json, src/main.py, ./lib/utils.ts
- Search patterns: "search for X", "find all Y", "grep for Z"
- Multiple items: "files X, Y, and Z", "check A and B"
"""

import _lib_path  # noqa: F401
import sys
import json
import re

from session_state import (
    load_state, save_state,
    add_pending_file, add_pending_search,
)


# =============================================================================
# EXTRACTION PATTERNS
# =============================================================================

# File path patterns
FILE_PATTERNS = [
    # Explicit file extensions
    r'[`"\']?([\w./\-]+\.(?:py|ts|tsx|js|jsx|json|yaml|yml|md|txt|toml|rs|go))[`"\']?',
    # Paths with directories
    r'[`"\']?((?:\.{0,2}/)?[\w\-]+/[\w./\-]+)[`"\']?',
]

# Search intention patterns
SEARCH_PATTERNS = [
    r'(?:search|grep|find|look)\s+(?:for\s+)?[`"\']?(\w+)[`"\']?',
    r'(?:search|grep|find)\s+[`"\']?([^`"\']+)[`"\']?\s+(?:in|across)',
]

# Multi-item patterns
MULTI_ITEM_PATTERNS = [
    r'files?\s*[:\s]+([^.]+)',  # "files: X, Y, Z"
    r'(?:check|read|examine)\s+(.+?)(?:\s+and\s+|\s*,\s*)(.+?)(?:\s+and\s+|\s*,\s*|$)',
]


def extract_files(text: str) -> list:
    """Extract file paths from text."""
    files = []

    for pattern in FILE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0]
            # Filter out obvious non-files
            if match and not match.startswith('http') and ('/' in match or '.' in match):
                # Normalize
                clean = match.strip('`"\'')
                if len(clean) > 3 and len(clean) < 200:
                    files.append(clean)

    return list(set(files))


def extract_searches(text: str) -> list:
    """Extract search patterns from text."""
    searches = []

    for pattern in SEARCH_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0]
            clean = match.strip()
            if len(clean) > 2 and len(clean) < 100:
                searches.append(clean)

    return list(set(searches))


def count_mentioned_items(text: str) -> int:
    """Count how many items (files/searches) are mentioned."""
    files = extract_files(text)
    searches = extract_searches(text)
    return len(files) + len(searches)


# =============================================================================
# MAIN
# =============================================================================

def main():
    """UserPromptSubmit hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit"}}))
        sys.exit(0)

    prompt = input_data.get("prompt", "")

    if not prompt:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit"}}))
        sys.exit(0)

    # Extract files and searches
    files = extract_files(prompt)
    searches = extract_searches(prompt)

    if not files and not searches:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit"}}))
        sys.exit(0)

    # Load state and track pending items
    state = load_state()

    for f in files:
        add_pending_file(state, f)

    for s in searches:
        add_pending_search(state, s)

    save_state(state)

    # If multiple items mentioned, inject batching reminder
    total = len(files) + len(searches)
    context = ""

    if total >= 2:
        items_preview = (files + searches)[:4]
        context = (
            f"⚡ DETECTED {total} ITEMS: {items_preview}\n"
            f"RULE: Batch ALL Read/Grep calls in ONE message. Do NOT read sequentially."
        )

    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
        }
    }

    if context:
        output["hookSpecificOutput"]["additionalContext"] = context

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
