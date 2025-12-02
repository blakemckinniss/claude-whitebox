#!/usr/bin/env python3
"""
Background Enforcer Hook v3.2: PreToolUse blocker for slow Bash commands.

Hook Type: PreToolUse
Latency Target: <10ms

THE CORE INSIGHT:
Slow commands (pytest, npm, pip install, cargo build) block the session.
Claude Code supports `run_in_background=true` but it's rarely used.

This hook:
1. Detects commands matching slow patterns
2. BLOCKS if run_in_background is not true
3. Forces async execution pattern

The result: Claude can continue working while tests/builds run.
"""

import sys
import json
from pathlib import Path

# Add lib to path
_lib_dir = str(Path(__file__).parent.parent / "lib")
if _lib_dir not in sys.path:
    sys.path.insert(0, _lib_dir)
from synapse_core import log_block, format_block_acknowledgment

# =============================================================================
# SLOW COMMAND PATTERNS
# =============================================================================

# Commands that typically take >5 seconds
SLOW_PATTERNS = [
    # Test runners
    "pytest", "npm test", "npm run test", "yarn test", "cargo test",
    "go test", "mvn test", "gradle test", "jest", "vitest",
    # Build tools
    "npm build", "npm run build", "yarn build", "cargo build",
    "go build", "mvn package", "gradle build", "make", "cmake",
    "webpack", "vite build", "tsc",
    # Package managers
    "pip install", "npm install", "yarn install", "cargo install",
    "go mod download", "bundle install", "composer install",
    # Container operations
    "docker build", "docker-compose up", "docker pull",
    # Linting (can be slow on large codebases)
    "eslint", "pylint", "mypy", "ruff check",
]

# Commands that are OK to run blocking (quick operations)
EXEMPT_PATTERNS = [
    "pip install --help",
    "npm --version", "npm -v",
    "pytest --help", "pytest --version",
    "--dry-run", "--help", "-h", "--version",
]


def extract_command_core(command: str) -> str:
    """Extract the core command, stripping heredocs and string literals.

    This prevents false positives from commit messages like:
    git commit -m "Added mypy cache to gitignore"
    """
    # For heredocs, strip everything after << FIRST (before other checks)
    # This handles: git commit -m "$(cat <<'EOF'\nMake...\nEOF)"
    if "<<" in command:
        command = command.split("<<")[0]

    # For git commit with -m, only check up to the message
    if "git commit" in command.lower():
        # Find -m and stop there (message content is irrelevant)
        parts = command.split()
        core_parts = []
        skip_next = False
        for part in parts:
            if skip_next:
                skip_next = False
                continue
            if part == "-m":
                skip_next = True  # Skip the message argument
                core_parts.append(part)
                continue
            if part.startswith("-m"):
                continue  # Skip -m"message" style
            core_parts.append(part)
        return " ".join(core_parts)

    # For commands with quoted strings, be conservative - check the whole thing
    # but fast commands like git are generally safe
    # Note: python3 -c is fast; slowness comes from pytest/npm directly invoked
    fast_commands = [
        "git ", "cd ", "ls ", "cat ", "echo ", "mkdir ", "rm ", "mv ", "cp ",
        "python3 -c", "python -c", "grep ", "head ", "tail ", "wc ", "sort ",
        "touch ", "chmod ", "chown ", "ln ", "pwd", "which ", "type ", "file ",
    ]
    if any(command.lower().startswith(fc) for fc in fast_commands):
        return ""  # Skip check entirely for fast commands

    return command


def is_slow_command(command: str) -> bool:
    """Check if command matches slow patterns."""
    # Extract core command to avoid false positives from string content
    core = extract_command_core(command)
    if not core:
        return False

    core_lower = core.lower()

    # Check exemptions first
    for exempt in EXEMPT_PATTERNS:
        if exempt in core_lower:
            return False

    # Check slow patterns
    for pattern in SLOW_PATTERNS:
        if pattern in core_lower:
            return True

    return False


def output_hook_result(event_name: str, decision: str = "approve",
                       reason: str = "", context: str = "",
                       tool_name: str = "", tool_input: dict = None):
    """Output standardized hook result. Logs blocks for Stop hook reflection."""
    result = {
        "hookSpecificOutput": {
            "hookEventName": event_name,
        }
    }

    if decision == "deny":
        result["decision"] = "block"
        result["reason"] = reason
        log_block("background_enforcer", reason, tool_name, tool_input)
        # Add acknowledgment prompt
        reason = reason + format_block_acknowledgment("background_enforcer")
    elif context:
        result["hookSpecificOutput"]["additionalContext"] = context

    print(json.dumps(result))


def main():
    """PreToolUse hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        output_hook_result("PreToolUse")
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Only check Bash commands
    if tool_name != "Bash":
        output_hook_result("PreToolUse")
        sys.exit(0)

    command = tool_input.get("command", "")
    is_background = tool_input.get("run_in_background", False)

    # Check if slow command without background flag
    if is_slow_command(command) and not is_background:
        # Extract the slow pattern for the message
        pattern_found = next(
            (p for p in SLOW_PATTERNS if p in command.lower()),
            "slow command"
        )

        reason = (
            f"⛔ USE BACKGROUND EXECUTION\n"
            f"Command contains `{pattern_found}` which is slow.\n"
            f"Re-issue with: run_in_background=true\n\n"
            f"Pattern:\n"
            f"1. Bash(command=\"{command[:50]}...\", run_in_background=true)\n"
            f"2. Continue working on other tasks\n"
            f"3. BashOutput(bash_id=<id>) to check results"
        )

        output_hook_result("PreToolUse", decision="deny", reason=reason,
                           tool_name=tool_name, tool_input=tool_input)
        sys.exit(0)

    # Warn if command looks potentially slow but not in our list
    suspicious_keywords = ["install", "build", "test", "compile"]
    if any(kw in command.lower() for kw in suspicious_keywords) and not is_background:
        context = (
            "⚡ POTENTIALLY SLOW: Command contains build/test keywords.\n"
            "Consider: run_in_background=true for commands >5s"
        )
        output_hook_result("PreToolUse", context=context)
        sys.exit(0)

    output_hook_result("PreToolUse")
    sys.exit(0)


if __name__ == "__main__":
    main()
