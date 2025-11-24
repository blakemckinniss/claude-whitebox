#!/usr/bin/env python3
"""
Organizational Drift Gate (PreToolUse Hook)
Blocks catastrophic file structure violations before they happen
"""

import sys
import json
from pathlib import Path

# Add scripts/lib to path
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root / "scripts" / "lib"))

from org_drift import check_organizational_drift


def main():
    # Read hook input from stdin
    hook_input = json.loads(sys.stdin.read())

    tool_name = hook_input.get("toolName")
    tool_params = hook_input.get("toolParams", {})

    # Only intercept Write and Edit operations
    if tool_name not in ["Write", "Edit"]:
        # Allow all other tools
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "Tool not subject to organizational drift checks"
            }
        }))
        return 0

    # Extract file path
    file_path = tool_params.get("file_path")
    if not file_path:
        # No file path - allow (shouldn't happen)
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "No file path specified"
            }
        }))
        return 0

    # Check for SUDO override in prompt context
    messages = hook_input.get("messages", [])
    is_sudo = any("SUDO" in msg.get("content", "") for msg in messages if isinstance(msg.get("content"), str))

    # Run drift detection
    allowed, errors, warnings = check_organizational_drift(
        file_path=file_path,
        repo_root=str(repo_root),
        is_sudo=is_sudo
    )

    # Build response message
    if errors:
        reason_parts = ["🚨 ORGANIZATIONAL DRIFT DETECTED:\n"]
        for error in errors:
            reason_parts.append(f"  • {error}")

        if is_sudo:
            reason_parts.append("\n⚠️  SUDO override detected - allowing operation (logged)")
            reason_parts.append("This violation has been recorded for pattern analysis.")
        else:
            reason_parts.append("\n❌ Operation BLOCKED")
            reason_parts.append("To override: Include 'SUDO' in your prompt")
            reason_parts.append("To report false positive: Run 'python scripts/lib/org_drift.py report FP <type>'")

        reason = "\n".join(reason_parts)
    else:
        reason = "Organizational drift checks passed"

    # Add warnings if present (don't block, just inform)
    if warnings:
        warning_msg = "\n\n⚠️  WARNINGS:\n" + "\n".join(f"  • {w}" for w in warnings)
        reason += warning_msg

    # Return decision
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow" if allowed else "deny",
            "permissionDecisionReason": reason
        }
    }))

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        # On error, allow operation but log error (MUST use stdout for hook protocol)
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": f"Hook error (allowing operation): {str(e)}"
            }
        }))  # CRITICAL: stdout, not stderr
        sys.exit(0)
