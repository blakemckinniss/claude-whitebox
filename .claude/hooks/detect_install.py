#!/usr/bin/env python3
"""
Detect Install Hook (PreToolUse)
Forces macgyver agent when install commands detected.

PURPOSE: Living off the Land enforcement - prevent dependency installation, force improvisation

TRIGGERS:
- Bash commands with: pip install, npm install, cargo install, apt-get install, brew install
- Package manager installation attempts

ACTION: Hard block + suggest macgyver agent delegation
"""

import sys
import json
import re

def main():
    # Read hook input from stdin
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_name = hook_input.get("toolName", "")
    tool_params = hook_input.get("toolParams", {})

    # Only process Bash tool
    if tool_name != "Bash":
        sys.exit(0)

    command = tool_params.get("command", "")

    # Detect package installation commands
    install_patterns = [
        r'\bpip3?\s+install\b',
        r'\bnpm\s+install\b',
        r'\bcargo\s+install\b',
        r'\bapt-get\s+install\b',
        r'\bbrew\s+install\b',
        r'\byum\s+install\b',
        r'\bdnf\s+install\b',
        r'\bpacman\s+-S\b',
    ]

    is_install_cmd = any(re.search(pattern, command, re.IGNORECASE) for pattern in install_patterns)

    if not is_install_cmd:
        sys.exit(0)

    # Extract what's being installed
    match = re.search(r'install\s+([a-zA-Z0-9_-]+)', command)
    package_name = match.group(1) if match else "package"

    message = f"""🚫 INSTALLATION BLOCKED: Living off the Land Protocol

Command: {command}
Package: {package_name}

RULE: Installing dependencies is BANNED. Use what's already on the system.

The macgyver agent enforces:
  ✅ Python stdlib solutions (urllib not requests)
  ✅ System binaries (curl, awk, sed, grep)
  ✅ Creative combinations (pipes, redirection)
  ✅ Zero external dependencies

RECOMMENDED ACTION:
  Use the Task tool with subagent_type='macgyver' to solve this with available tools.

Example:
  Use Task tool:
    subagent_type: macgyver
    description: Solve without installing {package_name}
    prompt: "Need {package_name} functionality but can't install. Find alternative using stdlib/system tools."

The macgyver agent will:
  1. Run inventory.py to see available tools
  2. Find creative solution using only installed binaries
  3. Provide fallback chain: stdlib → binaries → raw I/O

Why: Dependencies are technical debt. Improvisation > Installation.
See CLAUDE.md § MacGyver Protocol (Living off the Land)
"""

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": message
        }
    }))
    sys.exit(0)

if __name__ == "__main__":
    main()
