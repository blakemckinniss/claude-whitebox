#!/usr/bin/env python3
"""
Modularization Gate - Reminds Claude to modularize before creating/editing code.

Based on: https://www.reddit.com/r/ClaudeCode/comments/1p5bedc/modularization_hook/
Key insight: Descriptive filenames let Grep/Glob find code without reading contents = token savings.
"""

import json
import os
import sys

# Skip modularization reminder for these file types
SKIP_EXTENSIONS = {
    '.md', '.txt', '.rst',           # Documentation
    '.sh', '.bash', '.zsh',          # Shell scripts
    '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg',  # Config
    '.env', '.envrc',                # Environment
    '.gitignore', '.dockerignore',   # Ignore files
    '.lock',                         # Lock files
}

SKIP_PATHS = {
    '.claude/tmp/',
    'node_modules/',
    '__pycache__/',
    '.git/',
}


def should_skip(file_path: str) -> bool:
    """Check if file should skip modularization reminder."""
    if not file_path:
        return True

    # Check extension
    ext = os.path.splitext(file_path)[1].lower()
    if ext in SKIP_EXTENSIONS:
        return True

    # Check paths
    for skip_path in SKIP_PATHS:
        if skip_path in file_path:
            return True

    return False


def main():
    tool_input = json.loads(os.environ.get("CLAUDE_TOOL_INPUT", "{}"))
    file_path = tool_input.get("file_path", "")

    if should_skip(file_path):
        print(json.dumps({"status": "continue"}))
        return

    reminder = """📦 MODULARIZATION CHECK:
Before creating/editing, consider:
1. **Search first** - Does similar code already exist? (grep/glob before write)
2. **Separation** - Can this be split into logical modules (functions, classes, concerns)?
3. **Naming** - Use descriptive kebab-case filenames that explain purpose (LLM-friendly for search)
4. **Reusability** - Will this duplicate existing logic? Import instead of copy.

SKIP for: markdown, config, env, shell scripts.
INCLUDE in subagent prompts."""

    print(json.dumps({
        "status": "continue",
        "message": reminder
    }))


if __name__ == "__main__":
    main()
