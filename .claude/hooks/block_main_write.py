#!/usr/bin/env python3
"""
Block Main Write Hook (PreToolUse)
Forces script-smith agent for production code writes.

PURPOSE: Quality gate enforcement - prevent main assistant from writing production code without audit/void/drift

TRIGGERS:
- Write tool attempts to write to scripts/*, src/*, lib/*
- Production code locations (not scratch/)

ACTION: Hard block + suggest script-smith agent delegation
"""

import sys
import json
import os


def main():
    # Read hook input from stdin
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_name = hook_input.get("toolName", "")
    tool_params = hook_input.get("toolParams", {})

    # Only process Write tool
    if tool_name != "Write":
        sys.exit(0)

    file_path = tool_params.get("file_path", "")

    # Normalize path
    file_path = os.path.normpath(file_path)

    # Define production code directories
    production_dirs = ["scripts/", "src/", "lib/"]

    # Check if writing to production code
    is_production = any(file_path.startswith(d) or f"/{d}" in file_path for d in production_dirs)

    # Allow scratch/ writes
    if "scratch/" in file_path or file_path.startswith("scratch/"):
        sys.exit(0)

    if is_production:
        reason = f"""🛡️ PRODUCTION CODE WRITE BLOCKED

Target: {file_path}

RULE: Production code must go through script-smith agent (quality gates required).

The script-smith agent enforces:
  ✅ Scaffolding (correct imports, error handling)
  ✅ Security audit (secrets, SQL injection, XSS)
  ✅ Completeness check (no stubs, full error handling)
  ✅ Style consistency (matches project patterns)

RECOMMENDED ACTION:
  Use the Task tool with subagent_type='script-smith' to write this file.

Example:
  Use Task tool:
    subagent_type: script-smith
    description: Write production script
    prompt: "Create {file_path} with [requirements]"

Why: Direct writes bypass quality gates, leading to incomplete/insecure code.
See CLAUDE.md § Agent Delegation (script-smith)
"""

        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason
            }
        }))
        sys.exit(0)

    # Allow non-production writes
    sys.exit(0)

if __name__ == "__main__":
    main()
