#!/usr/bin/env python3
"""
Background Execution Opportunity Detector (PreToolUse:Bash)

Detects slow/long-running Bash commands and suggests run_in_background=true.

TRIGGERS:
- Test commands (pytest, npm test, cargo test)
- Build commands (npm run build, cargo build, make)
- Install commands (pip install, npm install)
- Database migrations
- Long-running scripts

ACTION: SOFT WARNING (suggest, don't block)
"""

import sys
import json
import os

# Slow command patterns
SLOW_PATTERNS = {
    "tests": ["pytest", "npm test", "npm run test", "cargo test", "python -m pytest", "jest", "vitest"],
    "builds": ["npm run build", "cargo build", "make", "webpack", "rollup", "vite build", "tsc"],
    "installs": ["pip install", "npm install", "npm ci", "cargo install", "apt-get install"],
    "docker": ["docker build", "docker-compose up", "docker run"],
    "migrations": ["migrate", "alembic", "flyway"],
    "processing": ["process", "convert", "generate", "compile"],
}

# Commands that should NEVER run in background
NEVER_BACKGROUND = [
    "cd ",
    "export ",
    "source ",
    ". ",
    "git rebase -i",
    "vim ",
    "nano ",
    "interactive",
]


def should_suggest_background(command):
    """
    Determine if command should run in background.

    Returns: (should_suggest: bool, category: str, reason: str)
    """
    command_lower = command.lower()

    # Check never-background patterns first
    for pattern in NEVER_BACKGROUND:
        if pattern in command_lower:
            return (False, "", "")

    # Check slow patterns
    for category, patterns in SLOW_PATTERNS.items():
        for pattern in patterns:
            if pattern in command_lower:
                reason = f"{category.upper()} command detected (typically slow)"
                return (True, category, reason)

    # Heuristic: Long command lines often mean complex operations
    if len(command) > 100:
        return (True, "complex", "Long command line (>100 chars)")

    # Heuristic: Piped commands often indicate processing
    if "|" in command and command.count("|") >= 2:
        return (True, "pipeline", "Multiple piped operations")

    return (False, "", "")


def check_if_already_background(tool_params):
    """Check if run_in_background is already set"""
    return tool_params.get("run_in_background", False)


def main():
    """Main detection logic"""
    try:
        data = json.load(sys.stdin)
    except:
        sys.exit(0)

    # Get command from tool parameters
    tool_params = data.get("parameters", {})
    command = tool_params.get("command", "")

    if not command:
        sys.exit(0)

    # Check if already using background
    if check_if_already_background(tool_params):
        # Already optimized, no suggestion needed
        sys.exit(0)

    # Analyze command
    should_suggest, category, reason = should_suggest_background(command)

    if should_suggest:
        message = f"""
💡 BACKGROUND EXECUTION OPPORTUNITY DETECTED

Command: {command[:80]}{'...' if len(command) > 80 else ''}
Category: {category.upper()}
Reason: {reason}

RECOMMENDATION: Use run_in_background=true

Why:
  • This command appears to be slow (estimated >5s)
  • Running in background = no blocking
  • You can continue working while it runs
  • Check results later with BashOutput tool

Pattern:
  Bash(
    command="{command[:40]}...",
    run_in_background=true,
    description="..."
  )

  [Continue with other work]

  # Later, check results:
  BashOutput(bash_id="<shell_id>")

Benefits:
  • Zero blocking time
  • Parallel execution possible
  • Better session efficiency

Note: This is a SUGGESTION, not a requirement.
      Use your judgment based on context.
"""

        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": message
            }
        }

        print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()
