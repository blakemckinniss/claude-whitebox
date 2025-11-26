#!/usr/bin/env python3
"""
Recursion Guard: PreToolUse hook blocking catastrophic folder duplication.

Hook Type: PreToolUse (matcher: Write|Edit|Bash)
Latency Target: <5ms

Blocks patterns like:
- .claude/.claude/
- projects/foo/projects/
- .claude/tmp/.claude/tmp/
- Any path with repeated directory segments
"""

import sys
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Patterns that indicate recursive folder catastrophe
RECURSIVE_PATTERNS = [
    r"\.claude/.*\.claude/",           # .claude inside .claude
    r"projects/[^/]+/projects/",       # projects inside projects
    r"\.claude/tmp/.*\.claude/tmp/",   # nested tmp dirs
    r"([^/]+)/\1/\1/",                 # any triple-nested same name
]

COMPILED_PATTERNS = [re.compile(p) for p in RECURSIVE_PATTERNS]


def output_result(decision: str = "approve", reason: str = ""):
    """Output hook result in PreToolUse specification format."""
    permission = "allow" if decision == "approve" else "deny"
    result = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": permission,
            "permissionDecisionReason": reason if reason else "Path validation passed"
        }
    }
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


def extract_path_from_bash(command: str) -> list[str]:
    """Extract potential paths from bash commands."""
    paths = []
    # mkdir patterns
    mkdir_match = re.findall(r'mkdir\s+(?:-p\s+)?["\']?([^"\';\s&|]+)', command)
    paths.extend(mkdir_match)
    # touch/cp/mv destination patterns
    for cmd in ['touch', 'cp', 'mv']:
        matches = re.findall(rf'{cmd}\s+[^;\s&|]+\s+["\']?([^"\';\s&|]+)', command)
        paths.extend(matches)
    # General path-like strings
    path_like = re.findall(r'["\']?(/[^"\';\s&|]+|\.claude/[^"\';\s&|]+|projects/[^"\';\s&|]+)', command)
    paths.extend(path_like)
    return paths


def is_recursive_path(path: str) -> tuple[bool, str]:
    """Check if path contains recursive folder patterns."""
    normalized = normalize_path(path)

    for pattern in COMPILED_PATTERNS:
        if pattern.search(normalized):
            return True, f"Matched pattern: {pattern.pattern}"

    # Additional check: same directory name appearing 2+ times in path
    parts = Path(normalized).parts
    seen = {}
    for part in parts:
        if part in ('.', '..'):
            continue
        seen[part] = seen.get(part, 0) + 1
        if seen[part] >= 2 and part not in ('src', 'lib', 'test', 'tests'):
            # Allow common legitimate duplicates but flag structural ones
            if part in ('.claude', 'projects', 'tmp', 'ops', 'hooks', 'commands'):
                return True, f"Duplicate structural directory: '{part}' appears {seen[part]}x"

    return False, ""


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        output_result()
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    paths_to_check = []

    if tool_name in ("Write", "Edit"):
        file_path = tool_input.get("file_path", "")
        if file_path:
            paths_to_check.append(file_path)
    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        paths_to_check.extend(extract_path_from_bash(command))
    else:
        output_result()
        sys.exit(0)

    for path in paths_to_check:
        is_recursive, reason = is_recursive_path(path)
        if is_recursive:
            output_result(
                decision="block",
                reason=f"🔁 **RECURSION CATASTROPHE BLOCKED**\n"
                       f"Path: {path}\n"
                       f"Reason: {reason}\n"
                       f"This creates nested duplicate structures. Use flat paths instead."
            )
            sys.exit(0)

    output_result()
    sys.exit(0)


if __name__ == "__main__":
    main()
