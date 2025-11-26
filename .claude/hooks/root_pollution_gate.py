#!/usr/bin/env python3
"""
Root Pollution Gate: PreToolUse hook blocking writes to repository root.

Hook Type: PreToolUse (matcher: Write|Edit)
Latency Target: <5ms

Enforces CLAUDE.md Hard Block #1:
"NEVER create new files in root. Use projects/, scratch/."
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Allowed top-level directories for writes
ALLOWED_PREFIXES = (
    "projects/",
    "scratch/",
    "scripts/",
    ".claude/",
)

# Files that ARE allowed at root (existing config files)
ALLOWED_ROOT_FILES = {
    ".gitignore",
    ".python-version",
    "pyproject.toml",
    "requirements.txt",
    "package.json",
    "Makefile",
    "README.md",
    "LICENSE",
    "CLAUDE.md",  # Project constitution - legitimate root config
}


def output_result(decision: str = "approve", reason: str = ""):
    """Output hook result."""
    result = {"hookSpecificOutput": {"hookEventName": "PreToolUse"}}
    if decision == "block":
        result["decision"] = "block"
        result["reason"] = reason
    print(json.dumps(result))


def normalize_path(file_path: str) -> str:
    """Convert to relative path from project root."""
    try:
        p = Path(file_path)
        if p.is_absolute():
            try:
                return str(p.relative_to(PROJECT_ROOT))
            except ValueError:
                return str(p)
        return str(p)
    except Exception:
        return file_path


def is_root_pollution(rel_path: str) -> bool:
    """Check if path pollutes repository root."""
    # Already in allowed directory
    if any(rel_path.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        return False

    # Allowed root config file
    if rel_path in ALLOWED_ROOT_FILES:
        return False

    # Check if it's a root-level file (no directory component)
    parts = Path(rel_path).parts
    if len(parts) == 1:
        # Single filename at root = pollution
        return True

    # Check if first directory is not allowed
    if parts[0] not in {"projects", "scratch", "scripts", ".claude"}:
        return True

    return False


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        output_result()
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    # Only check Write and Edit
    if tool_name not in ("Write", "Edit"):
        output_result()
        sys.exit(0)

    file_path = tool_input.get("file_path", "")
    if not file_path:
        output_result()
        sys.exit(0)

    rel_path = normalize_path(file_path)

    if is_root_pollution(rel_path):
        output_result(
            decision="block",
            reason=f"**ROOT POLLUTION BLOCKED** (Hard Block #1)\n"
                   f"Path: {rel_path}\n"
                   f"Use: projects/, scratch/, or scripts/ instead."
        )
        sys.exit(0)

    output_result()
    sys.exit(0)


if __name__ == "__main__":
    main()
